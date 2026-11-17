"""Verify Linux 7.2 FunctionFS MTP + ADB descriptors, composite setup, and concurrent service."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ZIG = Path(r"C:\Users\palpa\Tools\zig-x86_64-windows-0.17.0\zig.exe")


def test_ffs_mtp_adb_descriptors_mtp_stream_and_adb_protocol(tmp_path):
    hdr = ROOT / "scripts/peripheral_lab/usb_ffs_mtp_adb.h"
    src = tmp_path / "ffs_test.c"
    src.write_text(f'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "{hdr.as_posix()}"

static uint8_t tx_buf[131072];
static size_t tx_len;
static uint8_t fake_file[70000];
static size_t fake_file_len;
static int fail_write_at, write_calls;

static int mock_write_all(int fd, const void *buf, size_t len) {{
    assert(fd == 11);
    if (++write_calls == fail_write_at) {{ errno = EPIPE; return -1; }}
    assert(tx_len + len <= sizeof(tx_buf));
    memcpy(tx_buf + tx_len, buf, len);
    tx_len += len;
    return 0;
}}

static int mock_pread_chunk(int fd, void *buf, size_t len, uint64_t off) {{
    assert(fd == 22);
    if (off >= fake_file_len) return 0;
    size_t avail = fake_file_len - (size_t)off;
    size_t n = len < avail ? len : avail;
    memcpy(buf, fake_file + off, n);
    return (int)n;
}}

int main(void) {{
    struct r36_ffs_mtp_descriptors_v2 mtp;
    struct r36_ffs_adb_descriptors_v2 adb;
    uint8_t str_buf[64];

    r36_build_ffs_mtp_descriptors(&mtp);
    assert(mtp.magic == 3u && mtp.length == sizeof(mtp));
    assert(mtp.flags == (0x01u | 0x02u | 0x08u));
    assert(mtp.fs_count == 4u && mtp.hs_count == 4u && mtp.ms_os_count == 1u);
    assert(mtp.fs_intf.bNumEndpoints == 3u && mtp.hs_intf.bNumEndpoints == 3u);
    assert(mtp.fs_bulk_in.wMaxPacketSize == 64u && mtp.hs_bulk_in.wMaxPacketSize == 512u);
    assert(mtp.fs_bulk_out.wMaxPacketSize == 64u && mtp.hs_bulk_out.wMaxPacketSize == 512u);
    assert(mtp.fs_int_in.wMaxPacketSize == 28u && mtp.hs_int_in.wMaxPacketSize == 28u);
    assert(mtp.ms_os_header.wIndex == 0x0004u && mtp.ms_os_header.bCount == 1u);
    assert(!memcmp(mtp.ms_os_compat.CompatibleID, "MTP\\0\\0\\0\\0\\0", 8));

    r36_build_ffs_adb_descriptors(&adb);
    assert(adb.magic == 3u && adb.length == sizeof(adb));
    assert(adb.flags == (0x01u | 0x02u));
    assert(adb.fs_count == 3u && adb.hs_count == 3u);
    assert(adb.fs_intf.bInterfaceClass == 0xffu);
    assert(adb.fs_intf.bInterfaceSubClass == 0x42u);
    assert(adb.fs_intf.bInterfaceProtocol == 0x01u);
    assert(adb.hs_bulk_in.wMaxPacketSize == 512u && adb.hs_bulk_out.wMaxPacketSize == 512u);

    unsigned int total_tx = 2u + 1u;
    unsigned int total_rx = 1u + 1u;
    assert(total_tx == R36_MTP_ADB_REQUIRED_TX_EPS && total_tx <= R36_HC16XX_MUSB_MAX_TX_EPS);
    assert(total_rx == R36_MTP_ADB_REQUIRED_RX_EPS && total_rx <= R36_HC16XX_MUSB_MAX_RX_EPS);

    assert(r36_build_ffs_string(str_buf, 10, "MTP") == 0);
    size_t slen = r36_build_ffs_string(str_buf, sizeof(str_buf), "ADB Interface");
    assert(slen == 18 + strlen("ADB Interface") + 1);
    assert(!strcmp((const char *)(str_buf + 18), "ADB Interface"));

    fake_file_len = sizeof(fake_file);
    for (size_t i = 0; i < fake_file_len; i++) fake_file[i] = (uint8_t)(i * 13u + 3u);
    tx_len = 0; fail_write_at = 0; write_calls = 0;
    assert(r36_mtp_ffs_send_file_with_header(11, 22, 100, 50000, 0x1009u, 42u,
                                             mock_write_all, mock_pread_chunk) == 0);
    assert(tx_len == 50000 + 12);
    uint32_t hdr_len, hdr_tid; uint16_t hdr_type, hdr_op;
    memcpy(&hdr_len, tx_buf + 0, 4);
    memcpy(&hdr_type, tx_buf + 4, 2);
    memcpy(&hdr_op, tx_buf + 6, 2);
    memcpy(&hdr_tid, tx_buf + 8, 4);
    assert(hdr_len == 50012u && hdr_type == 2u && hdr_op == 0x1009u && hdr_tid == 42u);
    assert(!memcmp(tx_buf + 12, fake_file + 100, 50000));

    tx_len = 0; write_calls = 0; fail_write_at = 3;
    assert(r36_mtp_ffs_send_file_with_header(11, 22, 0, 50000, 0x1009u, 1u,
                                             mock_write_all, mock_pread_chunk) == -1);
    tx_len = 0; write_calls = 0; fail_write_at = 0;
    assert(r36_mtp_ffs_send_file_with_header(11, 22, 69000, 5000, 0x1009u, 1u,
                                             mock_write_all, mock_pread_chunk) == -1);

    const char banner[] = "device::ro.product.name=r36s;ro.product.model=R36S;";
    struct r36_adb_msg msg;
    r36_adb_pack(&msg, R36_ADB_CNXN, R36_ADB_VERSION, R36_ADB_MAXDATA, banner, (uint32_t)sizeof(banner));
    assert(r36_adb_validate(&msg, banner) == 0);
    msg.magic ^= 1u;
    assert(r36_adb_validate(&msg, banner) == -1);
    msg.magic ^= 1u;
    msg.data_check ^= 1u;
    assert(r36_adb_validate(&msg, banner) == -1);
    msg.data_check ^= 1u;
    msg.data_length = R36_ADB_MAXDATA + 1u;
    assert(r36_adb_validate(&msg, banner) == -1);

    struct r36_adb_session sess;
    struct r36_adb_msg in_msg, out_msg;
    uint8_t out_payload[256];
    memset(&sess, 0, sizeof(sess));
    r36_adb_pack(&in_msg, R36_ADB_OPEN, 7u, 0u, "shell:id\\0", 9u);
    assert(r36_adb_handle_packet(&sess, &in_msg, "shell:id\\0", &out_msg, out_payload, sizeof(out_payload)) == -1);

    r36_adb_pack(&in_msg, R36_ADB_CNXN, R36_ADB_VERSION, 4096u, "host::\\0", 7u);
    assert(r36_adb_handle_packet(&sess, &in_msg, "host::\\0", &out_msg, out_payload, sizeof(out_payload)) == 1);
    assert(sess.connected == 1 && out_msg.command == R36_ADB_CNXN);
    assert(r36_adb_validate(&out_msg, out_payload) == 0);

    r36_adb_pack(&in_msg, R36_ADB_OPEN, 7u, 0u, "shell:id\\0", 9u);
    assert(r36_adb_handle_packet(&sess, &in_msg, "shell:id\\0", &out_msg, out_payload, sizeof(out_payload)) == 1);
    assert(sess.stream_open == 1 && out_msg.command == R36_ADB_OKAY && out_msg.arg0 == 1u && out_msg.arg1 == 7u);

    r36_adb_pack(&in_msg, R36_ADB_WRTE, 7u, 1u, "uname\\n", 6u);
    assert(r36_adb_handle_packet(&sess, &in_msg, "uname\\n", &out_msg, out_payload, sizeof(out_payload)) == 1);
    assert(out_msg.command == R36_ADB_OKAY);

    r36_adb_pack(&in_msg, R36_ADB_CLSE, 7u, 1u, NULL, 0u);
    assert(r36_adb_handle_packet(&sess, &in_msg, NULL, &out_msg, out_payload, sizeof(out_payload)) == 1);
    assert(sess.stream_open == 0 && out_msg.command == R36_ADB_CLSE);

    tx_len = 0; write_calls = 0; fail_write_at = 0;
    assert(r36_ffs_init_mtp_ep0(11, mock_write_all) == 0);
    assert(write_calls == 2 && tx_len == sizeof(mtp) + 18 + 4);
    tx_len = 0; write_calls = 0; fail_write_at = 0;
    assert(r36_ffs_init_adb_ep0(11, mock_write_all) == 0);
    assert(write_calls == 2 && tx_len == sizeof(adb) + 18 + strlen("ADB Interface") + 1);
    return 0;
}}
''')
    exe = tmp_path / "ffs_test.exe"
    subprocess.run(["gcc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", str(src), "-o", str(exe)],
                   check=True, capture_output=True, timeout=20)
    subprocess.run([str(exe)], check=True, timeout=5)

    if ZIG.exists():
        mips_elf = tmp_path / "ffs_test_mips.elf"
        subprocess.run([str(ZIG), "cc", "-target", "mipsel-linux.4.4-musleabi", "-march=mips32r2",
                        "-msoft-float", "-static", "-Os", "-UNDEBUG", "-Wall", "-Wextra", "-Werror",
                        str(src), "-o", str(mips_elf)],
                       check=True, capture_output=True, timeout=30)
        assert mips_elf.stat().st_size > 0


def test_composite_mtp_adb_gadget_setup_ordering_and_concurrent_session(tmp_path):
    svc = ROOT / "scripts/peripheral_lab/usb_mtp_adb_service.c"
    build = (ROOT / "scripts/peripheral_lab/vm_build_kernel.sh").read_text()
    assert "--enable USB_CONFIGFS_F_FS" in build

    src = tmp_path / "composite_service_test.c"
    src.write_text(f'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

#define R36_USB_MTP_ADB_MOCK 1
#define R36_USB_MTP_ADB_LIBRARY_ONLY 1
#define O_WRONLY  1
#define O_RDWR    2
#define O_CLOEXEC 4
#define POLLIN    1

typedef int DIR;
struct dirent {{ char d_name[128]; }};
struct pollfd {{ int fd; short events; short revents; }};

#define FD_ATTR    10
#define FD_MTP_EP0 20
#define FD_MTP_IN  21
#define FD_MTP_OUT 22
#define FD_MTP_INT 23
#define FD_ADB_EP0 30
#define FD_ADB_IN  31
#define FD_ADB_OUT 32

static char current_attr[128];
static int step, fail_at, udcs, scans, dir_idx;
static int mtp_ep0_writes, adb_ep0_writes, udc_bound, udc_unbound;
static int ffs_mtp_mounted, ffs_adb_mounted;
static int open_mask;

static uint8_t mtp_rx_q[8][256];
static size_t  mtp_rx_len[8];
static int     mtp_rx_head, mtp_rx_tail;
static uint8_t mtp_tx_buf[8192];
static size_t  mtp_tx_len;

static uint8_t adb_rx_q[16][512];
static size_t  adb_rx_len[16];
static int     adb_rx_head, adb_rx_tail;
static uint8_t adb_tx_pkts[16][512];
static size_t  adb_tx_pkt_len[16];
static int     adb_tx_pkt_count;

static int mock_open(const char *p, int flags) {{
    (void)flags;
    if (++step == fail_at) {{ errno = EIO; return -1; }}
    snprintf(current_attr, sizeof(current_attr), "%s", p);
    if (!strcmp(p, "/dev/ffs-mtp/ep0")) {{ open_mask |= 1 << 0; return FD_MTP_EP0; }}
    if (!strcmp(p, "/dev/ffs-mtp/ep1")) {{ open_mask |= 1 << 1; return FD_MTP_IN; }}
    if (!strcmp(p, "/dev/ffs-mtp/ep2")) {{ open_mask |= 1 << 2; return FD_MTP_OUT; }}
    if (!strcmp(p, "/dev/ffs-mtp/ep3")) {{ open_mask |= 1 << 3; return FD_MTP_INT; }}
    if (!strcmp(p, "/dev/ffs-adb/ep0")) {{ open_mask |= 1 << 4; return FD_ADB_EP0; }}
    if (!strcmp(p, "/dev/ffs-adb/ep1")) {{ open_mask |= 1 << 5; return FD_ADB_IN; }}
    if (!strcmp(p, "/dev/ffs-adb/ep2")) {{ open_mask |= 1 << 6; return FD_ADB_OUT; }}
    return FD_ATTR;
}}

static int mock_close(int fd) {{
    if (fd == FD_MTP_EP0) open_mask &= ~(1 << 0);
    else if (fd == FD_MTP_IN)  open_mask &= ~(1 << 1);
    else if (fd == FD_MTP_OUT) open_mask &= ~(1 << 2);
    else if (fd == FD_MTP_INT) open_mask &= ~(1 << 3);
    else if (fd == FD_ADB_EP0) open_mask &= ~(1 << 4);
    else if (fd == FD_ADB_IN)  open_mask &= ~(1 << 5);
    else if (fd == FD_ADB_OUT) open_mask &= ~(1 << 6);
    else assert(fd == FD_ATTR);
    return 0;
}}

static ssize_t mock_write(int fd, const void *buf, size_t len) {{
    if (fd == FD_MTP_EP0) {{
        assert(ffs_mtp_mounted);
        if (++step == fail_at) {{ errno = EIO; return -1; }}
        mtp_ep0_writes++;
        return (ssize_t)len;
    }}
    if (fd == FD_ADB_EP0) {{
        assert(ffs_adb_mounted);
        if (++step == fail_at) {{ errno = EIO; return -1; }}
        adb_ep0_writes++;
        return (ssize_t)len;
    }}
    if (fd == FD_ATTR) {{
        if (!strcmp(current_attr, "UDC")) {{
            /* CRITICAL INVARIANT: UDC may only be bound AFTER both ffs.mtp/ep0
             * and ffs.adb/ep0 have received descriptors + strings (2 writes each). */
            assert(mtp_ep0_writes == 2 && adb_ep0_writes == 2);
            assert(open_mask == 0x7f);
            assert(!strcmp((const char *)buf, "musb-hdrc.0.auto"));
            udc_bound++;
        }} else if (!strcmp(current_attr, "/sys/kernel/config/usb_gadget/r36composite/UDC")) {{
            assert(!strcmp((const char *)buf, "\\n"));
            udc_unbound++;
        }}
        return (ssize_t)len;
    }}
    if (fd == FD_MTP_IN) {{
        assert(mtp_tx_len + len <= sizeof(mtp_tx_buf));
        memcpy(mtp_tx_buf + mtp_tx_len, buf, len);
        mtp_tx_len += len;
        return (ssize_t)len;
    }}
    if (fd == FD_ADB_IN) {{
        assert(adb_tx_pkt_count < 16 && len <= sizeof(adb_tx_pkts[0]));
        memcpy(adb_tx_pkts[adb_tx_pkt_count], buf, len);
        adb_tx_pkt_len[adb_tx_pkt_count] = len;
        adb_tx_pkt_count++;
        return (ssize_t)len;
    }}
    return -1;
}}

static ssize_t mock_read(int fd, void *buf, size_t len) {{
    if (fd == FD_MTP_OUT) {{
        assert(mtp_rx_head < mtp_rx_tail);
        size_t n = mtp_rx_len[mtp_rx_head];
        assert(n <= len);
        memcpy(buf, mtp_rx_q[mtp_rx_head], n);
        mtp_rx_head++;
        return (ssize_t)n;
    }}
    if (fd == FD_ADB_OUT) {{
        assert(adb_rx_head < adb_rx_tail);
        size_t n = adb_rx_len[adb_rx_head];
        assert(n <= len);
        memcpy(buf, adb_rx_q[adb_rx_head], n);
        adb_rx_head++;
        return (ssize_t)n;
    }}
    return -1;
}}

static int mock_mkdir(const char *p, int mode) {{
    (void)p; (void)mode;
    return ++step == fail_at ? -1 : 0;
}}

static int mock_mount(const char *src, const char *target, const char *fstype, unsigned long flags, const void *data) {{
    (void)flags; (void)data;
    if (++step == fail_at) {{ errno = EIO; return -1; }}
    if (!strcmp(fstype, "functionfs")) {{
        if (!strcmp(src, "mtp") && !strcmp(target, "/dev/ffs-mtp")) ffs_mtp_mounted = 1;
        if (!strcmp(src, "adb") && !strcmp(target, "/dev/ffs-adb")) ffs_adb_mounted = 1;
    }}
    return 0;
}}

static int mock_umount(const char *target) {{
    if (!strcmp(target, "/dev/ffs-mtp")) ffs_mtp_mounted = 0;
    if (!strcmp(target, "/dev/ffs-adb")) ffs_adb_mounted = 0;
    return 0;
}}

static int mock_chdir(const char *p) {{
    (void)p;
    return ++step == fail_at ? -1 : 0;
}}

static int mock_symlink(const char *a, const char *b) {{
    (void)a; (void)b;
    return ++step == fail_at ? -1 : 0;
}}

static int mock_unlink(const char *p) {{
    (void)p;
    return 0;
}}

static DIR *mock_opendir(const char *p) {{
    static DIR d;
    assert(!strcmp(p, "/sys/class/udc"));
    dir_idx = 0;
    scans++;
    return &d;
}}

static struct dirent *mock_readdir(DIR *d) {{
    static struct dirent e;
    (void)d;
    if (dir_idx++ >= udcs) return NULL;
    snprintf(e.d_name, sizeof(e.d_name), "%s", dir_idx == 1 ? "musb-hdrc.0.auto" : "extra-udc");
    return &e;
}}

static int mock_closedir(DIR *d) {{ (void)d; return 0; }}
static int mock_usleep(unsigned int us) {{ (void)us; return 0; }}

static int mock_poll(struct pollfd *pfds, unsigned long nfds, int timeout) {{
    (void)timeout;
    assert(nfds == 2);
    int r = 0;
    pfds[0].revents = 0;
    pfds[1].revents = 0;
    if (mtp_rx_head < mtp_rx_tail) {{ pfds[0].revents = POLLIN; r++; }}
    if (adb_rx_head < adb_rx_tail) {{ pfds[1].revents = POLLIN; r++; }}
    return r;
}}

#define open     mock_open
#define close    mock_close
#define read     mock_read
#define write    mock_write
#define mkdir    mock_mkdir
#define mount    mock_mount
#define umount   mock_umount
#define chdir    mock_chdir
#define symlink  mock_symlink
#define unlink   mock_unlink
#define opendir  mock_opendir
#define readdir  mock_readdir
#define closedir mock_closedir
#define usleep   mock_usleep
#define poll     mock_poll

#include "{svc.as_posix()}"

static void reset_env(void) {{
    step = fail_at = scans = dir_idx = 0;
    udcs = 1;
    mtp_ep0_writes = adb_ep0_writes = udc_bound = udc_unbound = 0;
    ffs_mtp_mounted = ffs_adb_mounted = 0;
    open_mask = 0;
    mtp_rx_head = mtp_rx_tail = 0;
    mtp_tx_len = 0;
    adb_rx_head = adb_rx_tail = 0;
    adb_tx_pkt_count = 0;
    errno = EIO;
}}

static void push_mtp_cmd(uint16_t op, uint32_t tid, uint32_t p0, int has_p0) {{
    uint8_t *dst = mtp_rx_q[mtp_rx_tail];
    uint32_t len = has_p0 ? 16u : 12u;
    uint16_t type = R36_MTP_CT_COMMAND;
    memcpy(dst + 0, &len, 4);
    memcpy(dst + 4, &type, 2);
    memcpy(dst + 6, &op, 2);
    memcpy(dst + 8, &tid, 4);
    if (has_p0) memcpy(dst + 12, &p0, 4);
    mtp_rx_len[mtp_rx_tail++] = len;
}}

static void push_adb_pkt(uint32_t cmd, uint32_t a0, uint32_t a1, const void *payload, uint32_t plen) {{
    struct r36_adb_msg m;
    r36_adb_pack(&m, cmd, a0, a1, payload, plen);
    memcpy(adb_rx_q[adb_rx_tail], &m, sizeof(m));
    adb_rx_len[adb_rx_tail++] = sizeof(m);
    if (plen > 0 && payload) {{
        memcpy(adb_rx_q[adb_rx_tail], payload, plen);
        adb_rx_len[adb_rx_tail++] = plen;
    }}
}}

static int test_shell_cb(const char *cmd, char *out, size_t cap) {{
    return snprintf(out, cap, "exec:%s\\n", cmd);
}}

int main(void) {{
    struct r36_mtp_adb_runtime rt;
    int total_steps;

    memset(&rt, 0, sizeof(rt));
    reset_env();
    assert(r36_setup_mtp_adb_gadget(&rt.fds) == 0);
    assert(udc_bound == 1 && !strcmp(rt.fds.last_phase, "bound"));
    assert(open_mask == 0x7f && ffs_mtp_mounted == 1 && ffs_adb_mounted == 1);
    total_steps = step;
    r36_teardown_mtp_adb_gadget(&rt.fds);
    assert(open_mask == 0 && ffs_mtp_mounted == 0 && ffs_adb_mounted == 0 && udc_unbound == 1);

    /* Fail-closed verification at every single setup step */
    for (int i = 1; i <= total_steps; i++) {{
        memset(&rt, 0, sizeof(rt));
        reset_env();
        fail_at = i;
        assert(r36_setup_mtp_adb_gadget(&rt.fds) == -1);
        assert(udc_bound == 0 && open_mask == 0 && ffs_mtp_mounted == 0 && ffs_adb_mounted == 0);
    }}

    /* Missing UDC and ambiguous (>1) UDC refused */
    memset(&rt, 0, sizeof(rt)); reset_env(); udcs = 0;
    assert(r36_setup_mtp_adb_gadget(&rt.fds) == -1 && udc_bound == 0 && scans == 30 && open_mask == 0);
    memset(&rt, 0, sizeof(rt)); reset_env(); udcs = 2;
    assert(r36_setup_mtp_adb_gadget(&rt.fds) == -1 && udc_bound == 0 && open_mask == 0);

    /* Concurrent interleaved MTP + ADB session */
    memset(&rt, 0, sizeof(rt));
    reset_env();
    assert(r36_setup_mtp_adb_gadget(&rt.fds) == 0);

    /* Step 1: Simultaneous MTP OpenSession + ADB CNXN */
    push_mtp_cmd(R36_MTP_OP_OpenSession, 1u, 1u, 1);
    push_adb_pkt(R36_ADB_CNXN, R36_ADB_VERSION, 4096u, "host::\\0", 7u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 2);
    assert(rt.mtp_session_open == 1 && rt.mtp_commands_handled == 1);
    assert(rt.adb.connected == 1 && rt.adb_packets_handled == 1);
    /* ADB CNXN reply = 2 bulk writes (24B header + banner payload) */
    assert(adb_tx_pkt_count == 2 && adb_tx_pkt_len[0] == 24);

    /* Step 2: Simultaneous MTP GetStorageIDs + ADB OPEN("shell:uname -r") */
    adb_tx_pkt_count = 0; mtp_tx_len = 0;
    push_mtp_cmd(R36_MTP_OP_GetStorageIDs, 2u, 0u, 0);
    push_adb_pkt(R36_ADB_OPEN, 9u, 0u, "shell:uname -r\\0", 15u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 2);
    assert(rt.mtp_commands_handled == 2 && mtp_tx_len == 20 + 12);
    /* ADB OPEN shell reply = A_OKAY (24B) + A_WRTE header (24B) + A_WRTE payload ("exec:uname -r\\n") */
    assert(adb_tx_pkt_count == 3);
    assert(!memcmp(adb_tx_pkts[2], "exec:uname -r\\n", 14));

    /* Step 3: Host acknowledges shell output with A_OKAY -> device closes stream with A_CLSE,
     * while MTP serves GetDeviceInfo concurrently */
    adb_tx_pkt_count = 0; mtp_tx_len = 0;
    push_mtp_cmd(R36_MTP_OP_GetDeviceInfo, 3u, 0u, 0);
    push_adb_pkt(R36_ADB_OKAY, 9u, 1u, NULL, 0u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 2);
    assert(rt.mtp_commands_handled == 3 && mtp_tx_len > 60);
    assert(adb_tx_pkt_count == 1 && adb_tx_pkt_len[0] == 24);
    struct r36_adb_msg clse_hdr;
    memcpy(&clse_hdr, adb_tx_pkts[0], 24);
    assert(clse_hdr.command == R36_ADB_CLSE && rt.adb.stream_open == 0);

    /* Step 4: ADB sync: real file SEND (adb push) -> STAT -> RECV (adb pull) -> QUIT */
    snprintf(rt.adb_sync_root, sizeof(rt.adb_sync_root), "%s", "{tmp_path.as_posix()}");
    adb_tx_pkt_count = 0;
    push_adb_pkt(R36_ADB_OPEN, 10u, 0u, "sync:\\0", 6u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 1);
    assert(rt.adb_sync_mode == 1 && adb_tx_pkt_count == 1);

    /* adb push ("SEND" + "hello.bin,33188" + "DATA" + "R36_ADB_PUSH_PAYLOAD" + "DONE") */
    adb_tx_pkt_count = 0;
    uint8_t send_stream[128];
    const char *spath = "hello.bin,33188";
    const char *sbody = "R36_ADB_PUSH_PAYLOAD";
    uint32_t spath_len = (uint32_t)strlen(spath);
    uint32_t sbody_len = (uint32_t)strlen(sbody);
    uint32_t mtime = 1700000000u;
    size_t spos = 0;
    memcpy(send_stream + spos, "SEND", 4); spos += 4;
    memcpy(send_stream + spos, &spath_len, 4); spos += 4;
    memcpy(send_stream + spos, spath, spath_len); spos += spath_len;
    memcpy(send_stream + spos, "DATA", 4); spos += 4;
    memcpy(send_stream + spos, &sbody_len, 4); spos += 4;
    memcpy(send_stream + spos, sbody, sbody_len); spos += sbody_len;
    memcpy(send_stream + spos, "DONE", 4); spos += 4;
    memcpy(send_stream + spos, &mtime, 4); spos += 4;
    push_adb_pkt(R36_ADB_WRTE, 10u, 1u, send_stream, (uint32_t)spos);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 1);
    assert(adb_tx_pkt_count == 3 && adb_tx_pkt_len[2] == 8 && !memcmp(adb_tx_pkts[2], "OKAY", 4));

    /* STAT the pushed file */
    adb_tx_pkt_count = 0;
    uint8_t stat_req[32];
    uint32_t fn_len = 9u;
    memcpy(stat_req + 0, "STAT", 4);
    memcpy(stat_req + 4, &fn_len, 4);
    memcpy(stat_req + 8, "hello.bin", 9);
    push_adb_pkt(R36_ADB_WRTE, 10u, 1u, stat_req, 17u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 1);
    uint32_t stat_size = 0;
    memcpy(&stat_size, adb_tx_pkts[2] + 8, 4);
    assert(adb_tx_pkt_count == 3 && adb_tx_pkt_len[2] == 16 && !memcmp(adb_tx_pkts[2], "STAT", 4) && stat_size == sbody_len);

    /* RECV (adb pull) the pushed file */
    adb_tx_pkt_count = 0;
    memcpy(stat_req + 0, "RECV", 4);
    push_adb_pkt(R36_ADB_WRTE, 10u, 1u, stat_req, 17u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == 1);
    assert(adb_tx_pkt_count == 3 && adb_tx_pkt_len[2] == 16 + sbody_len);
    assert(!memcmp(adb_tx_pkts[2], "DATA", 4));
    assert(!memcmp(adb_tx_pkts[2] + 8, sbody, sbody_len));
    assert(!memcmp(adb_tx_pkts[2] + 8 + sbody_len, "DONE", 4));

    /* Reject path traversal ("../escape") in SEND */
    memcpy(send_stream + 0, "SEND", 4);
    uint32_t bad_len = 9u;
    memcpy(send_stream + 4, &bad_len, 4);
    memcpy(send_stream + 8, "../escape", 9);
    push_adb_pkt(R36_ADB_WRTE, 10u, 1u, send_stream, 17u);
    assert(r36_mtp_adb_poll_once(&rt, 10, test_shell_cb) == -1);

    r36_teardown_mtp_adb_gadget(&rt.fds);
    assert(open_mask == 0 && udc_unbound == 1);
    return 0;
}}
''')
    exe = tmp_path / "composite_service_test.exe"
    subprocess.run(["gcc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                    "-I", str(ROOT / "scripts/peripheral_lab"),
                    str(src), "-o", str(exe)],
                   check=True, capture_output=True, timeout=20)
    subprocess.run([str(exe)], check=True, timeout=5)

    if ZIG.exists():
        mips_svc = tmp_path / "r36-usb-mtp-adb.elf"
        subprocess.run([
            str(ZIG), "cc", "-target", "mipsel-linux.4.4-musleabi",
            "-march=mips32r2", "-msoft-float", "-static", "-Os",
            "-Wall", "-Wextra", "-Werror",
            str(svc), "-o", str(mips_svc),
        ], check=True, capture_output=True, timeout=30)
        assert mips_svc.stat().st_size > 0
