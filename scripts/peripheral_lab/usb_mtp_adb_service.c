/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef R36_USB_MTP_ADB_MOCK
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#endif

#include "usb_ffs_mtp_adb.h"

/* Composite Linux 7.2 FunctionFS service running MTP (ffs.mtp) and ADB (ffs.adb)
 * simultaneously on HC16xx MUSB USB0 (idVendor=0x18d1, idProduct=0x4e22).
 *
 * Ordering contract required by drivers/usb/gadget/function/f_fs.c:
 *   1. Create configfs gadget, functions/ffs.mtp, functions/ffs.adb, and links
 *      in configs/c.1/.
 *   2. Mount functionfs instances "mtp" -> /dev/ffs-mtp and "adb" -> /dev/ffs-adb.
 *   3. Open both ep0 nodes and write FunctionFS v2 descriptors + strings so both
 *      instances enter FFS_ACTIVE.
 *   4. Open bulk/interrupt endpoints (/dev/ffs-mtp/ep1..3, /dev/ffs-adb/ep1..2).
 *   5. Bind the single UDC (musb-hdrc.0.auto) last.
 */

#define R36_COMPOSITE_GADGET_DIR "/sys/kernel/config/usb_gadget/r36composite"
#define R36_FFS_MTP_DIR          "/dev/ffs-mtp"
#define R36_FFS_ADB_DIR          "/dev/ffs-adb"

#define R36_MTP_CT_COMMAND  1u
#define R36_MTP_CT_DATA     2u
#define R36_MTP_CT_RESPONSE 3u

#define R36_MTP_OP_GetDeviceInfo           0x1001u
#define R36_MTP_OP_OpenSession             0x1002u
#define R36_MTP_OP_CloseSession            0x1003u
#define R36_MTP_OP_GetStorageIDs           0x1004u
#define R36_MTP_OP_GetStorageInfo          0x1005u
#define R36_MTP_OP_GetObjectHandles        0x1007u
#define R36_MTP_OP_GetObjectInfo           0x1008u
#define R36_MTP_OP_GetObject               0x1009u
#define R36_MTP_OP_GetDevicePropDesc       0x1014u
#define R36_MTP_OP_GetPartialObject        0x101Bu
#define R36_MTP_OP_GetObjectPropsSupported 0x9801u

#define R36_MTP_RC_OK                      0x2001u
#define R36_MTP_RC_GeneralError            0x2002u
#define R36_MTP_RC_OperationNotSupported   0x2005u
#define R36_MTP_RC_InvalidStorageID        0x2008u
#define R36_MTP_RC_InvalidObjectHandle     0x2009u
#define R36_MTP_RC_DevicePropNotSupported  0x200Au
#define R36_MTP_RC_SessionAlreadyOpen      0x201Eu

#define R36_MTP_STORAGE_ID                 0x00010001u

struct r36_composite_fds {
    int mtp_ep0;
    int mtp_in;
    int mtp_out;
    int mtp_int;
    int adb_ep0;
    int adb_in;
    int adb_out;
    char bound_udc[128];
    char last_phase[64];
};

struct r36_mtp_adb_runtime {
    struct r36_composite_fds fds;
    struct r36_adb_session   adb;
    int                      mtp_session_open;
    uint32_t                 mtp_session_id;
    int                      adb_sync_mode;
    int                      adb_pending_close;
    char                     adb_sync_root[256];
    char                     adb_send_path[512];
    uint8_t                  adb_send_buf[65536];
    size_t                   adb_send_len;
    int                      adb_send_active;
    uint8_t                  adb_pending_out[R36_ADB_MAXDATA];
    uint32_t                 adb_pending_len;
    unsigned int             mtp_commands_handled;
    unsigned int             adb_packets_handled;
};

static void r36_init_composite_fds(struct r36_composite_fds *f)
{
    memset(f, 0, sizeof(*f));
    f->mtp_ep0 = f->mtp_in = f->mtp_out = f->mtp_int = -1;
    f->adb_ep0 = f->adb_in = f->adb_out = -1;
    strcpy(f->last_phase, "not_started");
}

static int r36_write_all_fd(int fd, const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    size_t done = 0;
    while (done < len) {
        ssize_t n = write(fd, p + done, len - done);
        if (n < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        if (n == 0) {
            errno = EIO;
            return -1;
        }
        done += (size_t)n;
    }
    return 0;
}

static int r36_write_attr(const char *path, const char *text)
{
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    int rc;
    if (fd < 0) return -1;
    rc = r36_write_all_fd(fd, text, strlen(text));
    close(fd);
    return rc;
}

static int r36_mkdir_ok(const char *path)
{
    return (mkdir(path, 0755) == 0 || errno == EEXIST) ? 0 : -1;
}

static void r36_close_fd(int *fd)
{
    if (*fd >= 0) {
        close(*fd);
        *fd = -1;
    }
}

static void r36_teardown_mtp_adb_gadget(struct r36_composite_fds *f)
{
    if (f->bound_udc[0]) {
        r36_write_attr(R36_COMPOSITE_GADGET_DIR "/UDC", "\n");
        f->bound_udc[0] = 0;
    }
    r36_close_fd(&f->mtp_int);
    r36_close_fd(&f->mtp_out);
    r36_close_fd(&f->mtp_in);
    r36_close_fd(&f->mtp_ep0);
    r36_close_fd(&f->adb_out);
    r36_close_fd(&f->adb_in);
    r36_close_fd(&f->adb_ep0);
    umount(R36_FFS_MTP_DIR);
    umount(R36_FFS_ADB_DIR);
    unlink(R36_COMPOSITE_GADGET_DIR "/os_desc/c.1");
    unlink(R36_COMPOSITE_GADGET_DIR "/configs/c.1/ffs.mtp");
    unlink(R36_COMPOSITE_GADGET_DIR "/configs/c.1/ffs.adb");
}

static int r36_setup_mtp_adb_gadget(struct r36_composite_fds *f)
{
    DIR *dir;
    struct dirent *entry;

    r36_init_composite_fds(f);
    strcpy(f->last_phase, "configfs");
    if (r36_mkdir_ok("/sys/kernel/config"))
        return -1;
    if (mount("configfs", "/sys/kernel/config", "configfs", 0, NULL) != 0 && errno != EBUSY)
        return -1;
    if (r36_mkdir_ok(R36_COMPOSITE_GADGET_DIR) || chdir(R36_COMPOSITE_GADGET_DIR) != 0)
        return -1;

    strcpy(f->last_phase, "descriptors");
    if (r36_write_attr("idVendor", R36_MTP_ADB_VID) ||
        r36_write_attr("idProduct", R36_MTP_ADB_PID) ||
        r36_write_attr("bcdUSB", "0x0200") ||
        r36_write_attr("bcdDevice", "0x0100") ||
        r36_write_attr("bDeviceClass", "0x00") ||
        r36_write_attr("bDeviceSubClass", "0x00") ||
        r36_write_attr("bDeviceProtocol", "0x00"))
        return -1;

    if (r36_mkdir_ok("strings/0x409") ||
        r36_write_attr("strings/0x409/serialnumber", "R36S-MTP-ADB") ||
        r36_write_attr("strings/0x409/manufacturer", "TreeFrogUI") ||
        r36_write_attr("strings/0x409/product", "TreeFrogUI MTP+ADB"))
        return -1;

    if (r36_mkdir_ok("configs/c.1") ||
        r36_mkdir_ok("configs/c.1/strings/0x409") ||
        r36_write_attr("configs/c.1/strings/0x409/configuration", "MTP+ADB") ||
        r36_write_attr("configs/c.1/MaxPower", "250") ||
        r36_write_attr("configs/c.1/bmAttributes", "0x80"))
        return -1;

    strcpy(f->last_phase, "os_desc");
    if (r36_write_attr("os_desc/b_vendor_code", "1") ||
        r36_write_attr("os_desc/qw_sign", "MSFT100") ||
        symlink(R36_COMPOSITE_GADGET_DIR "/configs/c.1", "os_desc/c.1") != 0 ||
        r36_write_attr("os_desc/use", "1"))
        return -1;

    strcpy(f->last_phase, "functions");
    if (r36_mkdir_ok("functions/ffs.mtp") ||
        r36_mkdir_ok("functions/ffs.adb") ||
        symlink(R36_COMPOSITE_GADGET_DIR "/functions/ffs.mtp", "configs/c.1/ffs.mtp") != 0 ||
        symlink(R36_COMPOSITE_GADGET_DIR "/functions/ffs.adb", "configs/c.1/ffs.adb") != 0)
        return -1;

    strcpy(f->last_phase, "mount_ffs");
    if (r36_mkdir_ok(R36_FFS_MTP_DIR) ||
        mount("mtp", R36_FFS_MTP_DIR, "functionfs", 0, NULL) != 0 ||
        r36_mkdir_ok(R36_FFS_ADB_DIR) ||
        mount("adb", R36_FFS_ADB_DIR, "functionfs", 0, NULL) != 0)
        goto fail;

    strcpy(f->last_phase, "init_mtp_ep0");
    f->mtp_ep0 = open(R36_FFS_MTP_DIR "/ep0", O_RDWR | O_CLOEXEC);
    if (f->mtp_ep0 < 0 || r36_ffs_init_mtp_ep0(f->mtp_ep0, r36_write_all_fd) != 0)
        goto fail;

    strcpy(f->last_phase, "init_adb_ep0");
    f->adb_ep0 = open(R36_FFS_ADB_DIR "/ep0", O_RDWR | O_CLOEXEC);
    if (f->adb_ep0 < 0 || r36_ffs_init_adb_ep0(f->adb_ep0, r36_write_all_fd) != 0)
        goto fail;

    strcpy(f->last_phase, "open_data_eps");
    f->mtp_in  = open(R36_FFS_MTP_DIR "/ep1", O_RDWR | O_CLOEXEC);
    f->mtp_out = open(R36_FFS_MTP_DIR "/ep2", O_RDWR | O_CLOEXEC);
    f->mtp_int = open(R36_FFS_MTP_DIR "/ep3", O_RDWR | O_CLOEXEC);
    f->adb_in  = open(R36_FFS_ADB_DIR "/ep1", O_RDWR | O_CLOEXEC);
    f->adb_out = open(R36_FFS_ADB_DIR "/ep2", O_RDWR | O_CLOEXEC);
    if (f->mtp_in < 0 || f->mtp_out < 0 || f->mtp_int < 0 || f->adb_in < 0 || f->adb_out < 0)
        goto fail;

    strcpy(f->last_phase, "wait_udc");
    for (unsigned int attempt = 0; attempt < 30; attempt++) {
        unsigned int count = 0;
        dir = opendir("/sys/class/udc");
        if (dir) {
            while ((entry = readdir(dir))) {
                if (entry->d_name[0] == '.') continue;
                count++;
                snprintf(f->bound_udc, sizeof(f->bound_udc), "%.127s", entry->d_name);
            }
            closedir(dir);
        }
        if (count > 1) goto fail;
        if (count == 1) {
            strcpy(f->last_phase, "bind_udc");
            if (r36_write_attr("UDC", f->bound_udc) != 0) {
                f->bound_udc[0] = 0;
                goto fail;
            }
            strcpy(f->last_phase, "bound");
            return 0;
        }
        usleep(100000);
    }
    errno = ENODEV;
fail:
    f->bound_udc[0] = 0;
    r36_teardown_mtp_adb_gadget(f);
    return -1;
}

/* MTP container helpers over FunctionFS bulk endpoints */
static int r36_mtp_send_container(int ep_in, uint16_t type, uint16_t code, uint32_t tid,
                                  const void *payload, uint32_t payload_len)
{
    uint8_t buf[512];
    uint32_t total = 12u + payload_len;
    if (total > sizeof(buf)) {
        errno = EMSGSIZE;
        return -1;
    }
    memcpy(buf + 0, &total, 4);
    memcpy(buf + 4, &type, 2);
    memcpy(buf + 6, &code, 2);
    memcpy(buf + 8, &tid, 4);
    if (payload_len > 0 && payload)
        memcpy(buf + 12, payload, payload_len);
    return r36_write_all_fd(ep_in, buf, total);
}

static size_t r36_mtp_put_u16(uint8_t *dst, size_t off, uint16_t v)
{
    memcpy(dst + off, &v, 2);
    return off + 2;
}

static size_t r36_mtp_put_u32(uint8_t *dst, size_t off, uint32_t v)
{
    memcpy(dst + off, &v, 4);
    return off + 4;
}

static size_t r36_mtp_put_str(uint8_t *dst, size_t off, const char *s)
{
    size_t n = strlen(s);
    if (n == 0) {
        dst[off++] = 0;
        return off;
    }
    dst[off++] = (uint8_t)(n + 1);
    for (size_t i = 0; i <= n; i++) {
        uint16_t ch = (uint8_t)s[i];
        off = r36_mtp_put_u16(dst, off, ch);
    }
    return off;
}

/* Handle one MTP command container on /dev/ffs-mtp/ep2 -> ep1 */
static int r36_mtp_handle_one(struct r36_mtp_adb_runtime *rt, const uint8_t *pkt, size_t n)
{
    uint32_t len, tid, p0 = 0;
    uint16_t type, op, rc = R36_MTP_RC_OK;
    uint8_t data[256];
    size_t dlen = 0;

    if (n < 12) return -1;
    memcpy(&len, pkt + 0, 4);
    memcpy(&type, pkt + 4, 2);
    memcpy(&op, pkt + 6, 2);
    memcpy(&tid, pkt + 8, 4);
    if (type != R36_MTP_CT_COMMAND) return -1;
    if (n >= 16) memcpy(&p0, pkt + 12, 4);

    switch (op) {
    case R36_MTP_OP_GetDeviceInfo: {
        static const uint16_t ops[] = {
            R36_MTP_OP_GetDeviceInfo, R36_MTP_OP_OpenSession, R36_MTP_OP_CloseSession,
            R36_MTP_OP_GetStorageIDs, R36_MTP_OP_GetStorageInfo, R36_MTP_OP_GetObjectHandles,
            R36_MTP_OP_GetObjectInfo, R36_MTP_OP_GetObject, R36_MTP_OP_GetDevicePropDesc,
            R36_MTP_OP_GetPartialObject, R36_MTP_OP_GetObjectPropsSupported
        };
        dlen = r36_mtp_put_u16(data, dlen, 100);
        dlen = r36_mtp_put_u32(data, dlen, 6);
        dlen = r36_mtp_put_u16(data, dlen, 100);
        dlen = r36_mtp_put_str(data, dlen, "microsoft.com: 1.0;");
        dlen = r36_mtp_put_u16(data, dlen, 0);
        dlen = r36_mtp_put_u32(data, dlen, (uint32_t)(sizeof(ops) / sizeof(ops[0])));
        for (size_t i = 0; i < sizeof(ops) / sizeof(ops[0]); i++)
            dlen = r36_mtp_put_u16(data, dlen, ops[i]);
        dlen = r36_mtp_put_u32(data, dlen, 0); /* events */
        dlen = r36_mtp_put_u32(data, dlen, 1); /* device props */
        dlen = r36_mtp_put_u16(data, dlen, 0xD402u);
        dlen = r36_mtp_put_u32(data, dlen, 0); /* capture formats */
        dlen = r36_mtp_put_u32(data, dlen, 2); /* playback formats */
        dlen = r36_mtp_put_u16(data, dlen, 0x3000u);
        dlen = r36_mtp_put_u16(data, dlen, 0x3001u);
        dlen = r36_mtp_put_str(data, dlen, "TreeFrogUI");
        dlen = r36_mtp_put_str(data, dlen, "R36S");
        dlen = r36_mtp_put_str(data, dlen, "1.0");
        dlen = r36_mtp_put_str(data, dlen, "R36S-MTP-ADB");
        if (r36_mtp_send_container(rt->fds.mtp_in, R36_MTP_CT_DATA, op, tid, data, (uint32_t)dlen) != 0)
            return -1;
        break;
    }
    case R36_MTP_OP_OpenSession:
        rt->mtp_session_open = 1;
        rt->mtp_session_id = p0 ? p0 : 1u;
        break;
    case R36_MTP_OP_CloseSession:
        rt->mtp_session_open = 0;
        rt->mtp_session_id = 0;
        break;
    case R36_MTP_OP_GetStorageIDs:
        dlen = r36_mtp_put_u32(data, dlen, 1u);
        dlen = r36_mtp_put_u32(data, dlen, R36_MTP_STORAGE_ID);
        if (r36_mtp_send_container(rt->fds.mtp_in, R36_MTP_CT_DATA, op, tid, data, (uint32_t)dlen) != 0)
            return -1;
        break;
    default:
        rc = R36_MTP_RC_OperationNotSupported;
        break;
    }

    if (r36_mtp_send_container(rt->fds.mtp_in, R36_MTP_CT_RESPONSE, rc, tid, NULL, 0) != 0)
        return -1;
    rt->mtp_commands_handled++;
    return 0;
}

/* ADB packet TX over FunctionFS: 24-byte header and payload are separate USB bulk writes */
static int r36_adb_send_packet(int ep_in, const struct r36_adb_msg *msg, const void *payload)
{
    if (r36_write_all_fd(ep_in, msg, sizeof(*msg)) != 0)
        return -1;
    if (msg->data_length > 0 && payload) {
        if (r36_write_all_fd(ep_in, payload, msg->data_length) != 0)
            return -1;
    }
    return 0;
}

/* Handle one ADB packet (header + optional payload) on /dev/ffs-adb/ep2 -> ep1,
 * supporting CNXN, shell:<cmd>, and sync: (STAT / QUIT).
 */
typedef int (*r36_shell_exec_fn)(const char *cmd, char *out, size_t cap);

static int r36_adb_resolve_sync_path(const struct r36_mtp_adb_runtime *rt,
                                     const uint8_t *raw_path, size_t path_len,
                                     char *out, size_t cap)
{
    char rel[384];
    if (path_len == 0 || path_len >= sizeof(rel)) return -1;
    memcpy(rel, raw_path, path_len);
    rel[path_len] = 0;
    /* Strip optional ",<mode>" suffix used by ADB SEND */
    char *comma = strrchr(rel, ',');
    if (comma) *comma = 0;
    if (strstr(rel, "..")) return -1;
    if (rt->adb_sync_root[0]) {
        int n = snprintf(out, cap, "%s/%s", rt->adb_sync_root, rel[0] == '/' ? rel + 1 : rel);
        return (n > 0 && (size_t)n < cap) ? 0 : -1;
    }
    int n = snprintf(out, cap, "%s", rel);
    return (n > 0 && (size_t)n < cap) ? 0 : -1;
}

static int r36_adb_process_one(struct r36_mtp_adb_runtime *rt,
                               const struct r36_adb_msg *in_msg, const uint8_t *in_payload,
                               r36_shell_exec_fn shell_cb)
{
    struct r36_adb_msg out_msg;
    uint8_t out_payload[R36_ADB_MAXDATA];

    if (r36_adb_validate(in_msg, in_payload) != 0)
        return -1;

    if (in_msg->command == R36_ADB_CNXN) {
        if (r36_adb_handle_packet(&rt->adb, in_msg, in_payload, &out_msg, out_payload, sizeof(out_payload)) != 1)
            return -1;
        rt->adb_sync_mode = 0;
        rt->adb_send_active = 0;
        rt->adb_pending_close = 0;
        rt->adb_pending_len = 0;
        if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, out_payload) != 0)
            return -1;
        rt->adb_packets_handled++;
        return 0;
    }

    if (!rt->adb.connected)
        return -1;

    if (in_msg->command == R36_ADB_OPEN) {
        char service[256];
        size_t slen = in_msg->data_length < sizeof(service) - 1 ? in_msg->data_length : sizeof(service) - 1;
        memcpy(service, in_payload, slen);
        service[slen] = 0;

        if (r36_adb_handle_packet(&rt->adb, in_msg, in_payload, &out_msg, out_payload, sizeof(out_payload)) != 1)
            return -1;
        /* Send A_OKAY first */
        if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, NULL) != 0)
            return -1;

        if (!strncmp(service, "shell:", 6)) {
            char reply[1024] = {0};
            const char *cmd = service + 6;
            int rlen = shell_cb ? shell_cb(cmd, reply, sizeof(reply) - 1) : snprintf(reply, sizeof(reply), "OK:%s\n", cmd);
            if (rlen < 0) rlen = 0;
            rt->adb_sync_mode = 0;
            rt->adb_send_active = 0;
            rt->adb_pending_close = 1;
            r36_adb_pack(&out_msg, R36_ADB_WRTE, rt->adb.local_id, rt->adb.remote_id, reply, (uint32_t)rlen);
            if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, reply) != 0)
                return -1;
        } else if (!strcmp(service, "sync:")) {
            rt->adb_sync_mode = 1;
            rt->adb_send_active = 0;
            rt->adb_pending_close = 0;
        }
        rt->adb_packets_handled++;
        return 0;
    }

    if (in_msg->command == R36_ADB_OKAY) {
        if (rt->adb_pending_close && rt->adb.stream_open) {
            rt->adb_pending_close = 0;
            rt->adb.stream_open = 0;
            r36_adb_pack(&out_msg, R36_ADB_CLSE, rt->adb.local_id, rt->adb.remote_id, NULL, 0);
            if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, NULL) != 0)
                return -1;
        }
        rt->adb_packets_handled++;
        return 0;
    }

    if (in_msg->command == R36_ADB_WRTE) {
        if (r36_adb_handle_packet(&rt->adb, in_msg, in_payload, &out_msg, out_payload, sizeof(out_payload)) != 1)
            return -1;
        /* Acknowledge host's WRTE with A_OKAY */
        if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, NULL) != 0)
            return -1;

        if (rt->adb_sync_mode && in_msg->data_length >= 8) {
            uint32_t arg_len = 0;
            memcpy(&arg_len, in_payload + 4, 4);
            if (!memcmp(in_payload, "STAT", 4) && 8u + arg_len <= in_msg->data_length) {
                char path[512];
                uint8_t stat_resp[16];
                uint32_t mode = 0, size = 0, mtime = 0;
                if (r36_adb_resolve_sync_path(rt, in_payload + 8, arg_len, path, sizeof(path)) == 0) {
                    FILE *fp = fopen(path, "rb");
                    if (fp) {
                        if (fseek(fp, 0, SEEK_END) == 0) {
                            long pos = ftell(fp);
                            if (pos >= 0) size = (uint32_t)pos;
                        }
                        fclose(fp);
                        mode = 0100644u;
                        mtime = 1700000000u;
                    }
                }
                memcpy(stat_resp + 0, "STAT", 4);
                memcpy(stat_resp + 4, &mode, 4);
                memcpy(stat_resp + 8, &size, 4);
                memcpy(stat_resp + 12, &mtime, 4);
                r36_adb_pack(&out_msg, R36_ADB_WRTE, rt->adb.local_id, rt->adb.remote_id, stat_resp, sizeof(stat_resp));
                if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, stat_resp) != 0)
                    return -1;
            } else if (!memcmp(in_payload, "RECV", 4) && 8u + arg_len <= in_msg->data_length) {
                /* adb pull: stream DATA + len + bytes, then DONE + 0 */
                char path[512];
                FILE *fp = NULL;
                if (r36_adb_resolve_sync_path(rt, in_payload + 8, arg_len, path, sizeof(path)) == 0)
                    fp = fopen(path, "rb");
                if (!fp) {
                    uint8_t fail_pkt[12];
                    uint32_t flen = 4;
                    memcpy(fail_pkt + 0, "FAIL", 4);
                    memcpy(fail_pkt + 4, &flen, 4);
                    memcpy(fail_pkt + 8, "ENOENT", 4);
                    r36_adb_pack(&out_msg, R36_ADB_WRTE, rt->adb.local_id, rt->adb.remote_id, fail_pkt, sizeof(fail_pkt));
                    if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, fail_pkt) != 0)
                        return -1;
                } else {
                    uint8_t sync_pkt[2048 + 16];
                    size_t nread = fread(sync_pkt + 8, 1, 2048, fp);
                    fclose(fp);
                    uint32_t clen = (uint32_t)nread, zero = 0;
                    memcpy(sync_pkt + 0, "DATA", 4);
                    memcpy(sync_pkt + 4, &clen, 4);
                    memcpy(sync_pkt + 8 + nread, "DONE", 4);
                    memcpy(sync_pkt + 12 + nread, &zero, 4);
                    r36_adb_pack(&out_msg, R36_ADB_WRTE, rt->adb.local_id, rt->adb.remote_id,
                                 sync_pkt, (uint32_t)(16 + nread));
                    if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, sync_pkt) != 0)
                        return -1;
                }
            } else if (!memcmp(in_payload, "SEND", 4) && 8u + arg_len <= in_msg->data_length) {
                /* adb push start: "SEND" + path_len + "<path>,<mode>" (optionally followed by DATA/DONE in same WRTE) */
                if (r36_adb_resolve_sync_path(rt, in_payload + 8, arg_len, rt->adb_send_path, sizeof(rt->adb_send_path)) != 0)
                    return -1;
                rt->adb_send_len = 0;
                rt->adb_send_active = 1;
                size_t pos = 8u + arg_len;
                while (pos + 8u <= in_msg->data_length) {
                    uint32_t sub_len = 0;
                    memcpy(&sub_len, in_payload + pos + 4, 4);
                    if (!memcmp(in_payload + pos, "DATA", 4) && pos + 8u + sub_len <= in_msg->data_length) {
                        if (rt->adb_send_len + sub_len > sizeof(rt->adb_send_buf)) return -1;
                        memcpy(rt->adb_send_buf + rt->adb_send_len, in_payload + pos + 8, sub_len);
                        rt->adb_send_len += sub_len;
                        pos += 8u + sub_len;
                    } else if (!memcmp(in_payload + pos, "DONE", 4)) {
                        FILE *fp = fopen(rt->adb_send_path, "wb");
                        if (!fp || fwrite(rt->adb_send_buf, 1, rt->adb_send_len, fp) != rt->adb_send_len) {
                            if (fp) fclose(fp);
                            return -1;
                        }
                        fclose(fp);
                        rt->adb_send_active = 0;
                        uint8_t okay_resp[8] = { 'O', 'K', 'A', 'Y', 0, 0, 0, 0 };
                        r36_adb_pack(&out_msg, R36_ADB_WRTE, rt->adb.local_id, rt->adb.remote_id, okay_resp, sizeof(okay_resp));
                        if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, okay_resp) != 0)
                            return -1;
                        break;
                    } else {
                        break;
                    }
                }
            } else if (!memcmp(in_payload, "QUIT", 4)) {
                rt->adb_sync_mode = 0;
                rt->adb_send_active = 0;
                rt->adb.stream_open = 0;
                r36_adb_pack(&out_msg, R36_ADB_CLSE, rt->adb.local_id, rt->adb.remote_id, NULL, 0);
                if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, NULL) != 0)
                    return -1;
            }
        }
        rt->adb_packets_handled++;
        return 0;
    }

    if (in_msg->command == R36_ADB_CLSE) {
        if (r36_adb_handle_packet(&rt->adb, in_msg, in_payload, &out_msg, out_payload, sizeof(out_payload)) != 1)
            return -1;
        rt->adb_sync_mode = 0;
        rt->adb_send_active = 0;
        rt->adb_pending_close = 0;
        if (r36_adb_send_packet(rt->fds.adb_in, &out_msg, NULL) != 0)
            return -1;
        rt->adb_packets_handled++;
        return 0;
    }

    return -1;
}

/* Multiplexed poll step servicing both MTP (ep2->ep1) and ADB (ep2->ep1) concurrently */
static int r36_mtp_adb_poll_once(struct r36_mtp_adb_runtime *rt, int timeout_ms, r36_shell_exec_fn shell_cb)
{
    struct pollfd pfds[2] = {
        { .fd = rt->fds.mtp_out, .events = POLLIN, .revents = 0 },
        { .fd = rt->fds.adb_out, .events = POLLIN, .revents = 0 },
    };
    int ready = poll(pfds, 2, timeout_ms);
    if (ready <= 0)
        return ready;

    if (pfds[0].revents & POLLIN) {
        uint8_t mtp_rx[512];
        ssize_t n = read(rt->fds.mtp_out, mtp_rx, sizeof(mtp_rx));
        if (n < 0 || r36_mtp_handle_one(rt, mtp_rx, (size_t)n) != 0)
            return -1;
    }
    if (pfds[1].revents & POLLIN) {
        struct r36_adb_msg hdr;
        uint8_t payload[R36_ADB_MAXDATA];
        ssize_t n = read(rt->fds.adb_out, &hdr, sizeof(hdr));
        if (n != (ssize_t)sizeof(hdr) || hdr.data_length > R36_ADB_MAXDATA)
            return -1;
        if (hdr.data_length > 0) {
            ssize_t pn = read(rt->fds.adb_out, payload, hdr.data_length);
            if (pn != (ssize_t)hdr.data_length)
                return -1;
        }
        if (r36_adb_process_one(rt, &hdr, hdr.data_length ? payload : NULL, shell_cb) != 0)
            return -1;
    }
    return ready;
}

#ifndef R36_USB_MTP_ADB_LIBRARY_ONLY
static int default_shell_cb(const char *cmd, char *out, size_t cap)
{
    return snprintf(out, cap, "r36s:%s\n", cmd);
}

int main(void)
{
    struct r36_mtp_adb_runtime rt;
    memset(&rt, 0, sizeof(rt));
    if (r36_setup_mtp_adb_gadget(&rt.fds) != 0)
        return 1;
    for (unsigned int i = 0; i < 100; i++) {
        if (r36_mtp_adb_poll_once(&rt, 100, default_shell_cb) < 0)
            break;
    }
    r36_teardown_mtp_adb_gadget(&rt.fds);
    return 0;
}
#endif
