"""Offline tests for the permanent (non-watchdog, zero-SD-write) release cold-boot shim."""
from pathlib import Path
import struct
import sys

import pytest
import unicorn as un
from unicorn import mips_const as mr

BOOT_CRYPTO = Path(__file__).resolve().parent
if str(BOOT_CRYPTO) not in sys.path:
    sys.path.insert(0, str(BOOT_CRYPTO))

from build_release_cold_candidate import (  # noqa: E402
    RELEASE_MAGIC,
    SHIM,
    WDT_CTRL_KSEG1,
    build_release_candidate,
    make_release_shim,
)
from loader_fs_probe import RESTORE_RECEIPT  # noqa: E402

ROOT = BOOT_CRYPTO.parents[1]


def test_release_shim_disables_wdt_sets_uhi_and_jumps():
    entry = 0x80512340
    dtb = 0x80720000
    tag = 0xCAFEBABE
    code = make_release_shim(SHIM, entry, dtb, tag)
    assert 32 <= len(code) <= 512

    cpu = un.Uc(un.UC_ARCH_MIPS, un.UC_MODE_MIPS32 | un.UC_MODE_LITTLE_ENDIAN)
    cpu.ctl_set_cpu_model(mr.UC_CPU_MIPS32_74KF)
    cpu.mem_map(0, 64 * 1024 * 1024)
    cpu.mem_map(0x18818000, 4096)
    cpu.mem_write(WDT_CTRL_KSEG1 & 0x1FFFFFFF, struct.pack("<I", 0x26))
    cpu.mem_write(SHIM & 0x1FFFFFFF, code)

    cpu.emu_start(SHIM, entry, count=2000)

    assert (cpu.reg_read(mr.UC_MIPS_REG_PC) & 0xFFFFFFFF) == entry
    assert (cpu.reg_read(mr.UC_MIPS_REG_A0) & 0xFFFFFFFF) == 0xFFFFFFFE
    assert (cpu.reg_read(mr.UC_MIPS_REG_A1) & 0xFFFFFFFF) == dtb
    assert cpu.reg_read(mr.UC_MIPS_REG_A2) == 0
    assert cpu.reg_read(mr.UC_MIPS_REG_A3) == 0
    assert struct.unpack("<I", cpu.mem_read(WDT_CTRL_KSEG1 & 0x1FFFFFFF, 4))[0] == 0

    receipt = struct.unpack("<16I", cpu.mem_read(RESTORE_RECEIPT & 0x1FFFFFFF, 64))
    assert receipt[0] == RELEASE_MAGIC
    assert receipt[2] == tag
    assert receipt[3] == 0  # no SD restore
    assert receipt[7] == 6
    assert receipt[8] == entry
    assert receipt[9] == dtb
    assert receipt[10] == 0  # watchdog disabled


def test_build_release_candidate_if_profile_present(tmp_path):
    profile = ROOT / "payload/kernel_full_session_v43"
    stock = ROOT / "analysis/boot_crypto/original_advapi32.dll"
    tpl = ROOT / "analysis/card2_files/kdump/tpl_decrypted.bin"
    if not (profile.exists() and stock.exists() and tpl.exists()):
        pytest.skip("local built kernel profile or stock boot assets absent")

    out = tmp_path / "release_v43_test"
    rec = build_release_candidate(profile, out)
    assert rec["mode"] == "permanent_release"
    assert rec["watchdog_seconds"] == 0
    assert rec["unicorn_emulation"]["status"] == "PASS"
    assert rec["unicorn_emulation"]["wdt_ctrl_after"] == 0
    assert (out / "advapi32.dll.release.NOT_DEPLOYED").stat().st_size == stock.stat().st_size
