"""Verify Linux 7.2 FunctionFS MTP + ADB descriptors, endpoint budget, and protocol framing."""
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

    /* Combined TX/RX endpoint count must fit HC16xx MUSB FIFO table (5 TX + 5 RX) */
    unsigned int total_tx = 2u + 1u;
    unsigned int total_rx = 1u + 1u;
    assert(total_tx == R36_MTP_ADB_REQUIRED_TX_EPS && total_tx <= R36_HC16XX_MUSB_MAX_TX_EPS);
    assert(total_rx == R36_MTP_ADB_REQUIRED_RX_EPS && total_rx <= R36_HC16XX_MUSB_MAX_RX_EPS);

    assert(r36_build_ffs_string(str_buf, 10, "MTP") == 0);
    size_t slen = r36_build_ffs_string(str_buf, sizeof(str_buf), "ADB Interface");
    assert(slen == 18 + strlen("ADB Interface") + 1);
    assert(!strcmp((const char *)(str_buf + 18), "ADB Interface"));

    /* Chunked FunctionFS MTP file-range transfer */
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

    /* Write error propagation */
    tx_len = 0; write_calls = 0; fail_write_at = 3;
    assert(r36_mtp_ffs_send_file_with_header(11, 22, 0, 50000, 0x1009u, 1u,
                                             mock_write_all, mock_pread_chunk) == -1);
    /* Short/truncated file read rejected */
    tx_len = 0; write_calls = 0; fail_write_at = 0;
    assert(r36_mtp_ffs_send_file_with_header(11, 22, 69000, 5000, 0x1009u, 1u,
                                             mock_write_all, mock_pread_chunk) == -1);

    /* ADB framing + checksum + negative controls */
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

    /* ADB session state machine: reject OPEN before CNXN, accept CNXN->OPEN->WRTE->CLSE */
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

    /* FunctionFS ep0 descriptor + string write helpers */
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
