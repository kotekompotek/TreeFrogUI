"""Build a permanent (non-watchdog, zero-SD-write) Linux 7 release advapi32.dll image
for HC16E310 and verify its MIPS32 shim in Unicorn 74Kf emulation."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import secrets
import struct

import unicorn as un
from unicorn import mips_const as mr

from capture_dtb import properties
from codec import decrypt, encrypt, make_uimage, parse_uimage, recover_key, unpack_loader
from emulate_loader_image import validate
from loader_fs_probe import Assembly, RESTORE_RECEIPT, move, store

ROOT = Path(__file__).resolve().parents[2]
SHIM = 0x80010000
RELEASE_MAGIC = 0x52454C31  # "REL1"
WDT_CTRL_KSEG1 = 0xB8818504


def make_release_shim(base: int, kernel_entry: int, dtb_address: int, tag: int) -> bytes:
    """Emit minimal MIPS32 release shim:
    1. Explicitly disable hardware watchdog control (0xB8818504 = 0).
    2. Write 64-byte release receipt (REL1, watchdog=0) at RESTORE_RECEIPT.
    3. Set UHI registers (a0=0xFFFFFFFE, a1=dtb, a2=0, a3=0) and jump to kernel_entry.
    Zero SD card writes before Linux boots (avoids power-loss FAT corruption).
    """
    a = Assembly(base)
    # Explicitly disable hardware watchdog control register
    a.constant(8, WDT_CTRL_KSEG1)
    a.emit(store(0, 0, 8), 0x0000000F)  # sw zero, 0(t0); sync

    # Populate 64-byte release receipt at RESTORE_RECEIPT (0xA2F91E00)
    a.constant(8, RESTORE_RECEIPT)
    values = [
        0,              # [0] magic written last after fields settle
        1,              # [1] version
        tag,            # [2] session_tag
        0,              # [3] stock_restore_performed = 0 (permanent release)
        0,              # [4] reserved
        0,              # [5] reserved
        0,              # [6] reserved
        6,              # [7] stage = 6 (direct kernel handoff)
        kernel_entry,   # [8] kernel entry
        dtb_address,    # [9] inline DTB address
        0,              # [10] watchdog_seconds = 0 (disabled)
        0, 0, 0, 0, 0,
    ]
    for index, value in enumerate(values):
        a.constant(9, value)
        a.emit(store(9, 4 * index, 8))
    a.constant(9, RELEASE_MAGIC)
    a.emit(store(9, 0, 8), 0x0000000F)

    # UHI Linux kernel handoff: a0=-2, a1=FDT, a2=0, a3=0 -> jr.hb t9; nop
    a.constant(4, 0xFFFFFFFE)
    a.constant(5, dtb_address)
    a.emit(move(6, 0), move(7, 0))
    a.constant(25, kernel_entry)
    a.emit(0x03200408, 0)  # jr.hb t9; nop
    return a.finish()


def emulate_release_candidate(folder: Path) -> dict:
    """Decrypt and emulate the built release candidate from SHIM to kernel_entry in Unicorn 74Kf."""
    manifest = json.loads((folder / "manifest.json").read_text())
    source = (ROOT / "analysis/card2_files/kdump/tpl_decrypted.bin").read_bytes()
    wrapped = (folder / "advapi32.dll.release.NOT_DEPLOYED").read_bytes()
    plain = decrypt(wrapped, recover_key(source))
    raw = gzip.decompress(plain[64:])

    shim_va = int(manifest["probe_entry"], 0)
    kernel_entry = int(manifest["original_entry"], 0)
    dtb_address = int(manifest["inline_dtb"], 0)
    tag = int(manifest["session_tag"], 0)

    cpu = un.Uc(un.UC_ARCH_MIPS, un.UC_MODE_MIPS32 | un.UC_MODE_LITTLE_ENDIAN)
    cpu.ctl_set_cpu_model(mr.UC_CPU_MIPS32_74KF)
    cpu.mem_map(0, 64 * 1024 * 1024)
    cpu.mem_map(0x18818000, 4096)
    # Seed WDT control with non-zero to prove shim clears it to 0
    cpu.mem_write(0x18818504, struct.pack("<I", 0x26))
    cpu.mem_write(0, raw)

    wdt_writes = []

    def on_wdt_write(uc, access, addr, size, val, user):
        wdt_writes.append((addr & 0x1FFFFFFF, size, val))

    cpu.hook_add(un.UC_HOOK_MEM_WRITE, on_wdt_write, begin=0x18818500, end=0x1881850F)
    cpu.emu_start(shim_va, kernel_entry, count=5000)

    pc = cpu.reg_read(mr.UC_MIPS_REG_PC) & 0xFFFFFFFF
    a0 = cpu.reg_read(mr.UC_MIPS_REG_A0) & 0xFFFFFFFF
    a1 = cpu.reg_read(mr.UC_MIPS_REG_A1) & 0xFFFFFFFF
    a2 = cpu.reg_read(mr.UC_MIPS_REG_A2) & 0xFFFFFFFF
    a3 = cpu.reg_read(mr.UC_MIPS_REG_A3) & 0xFFFFFFFF
    wdt_ctrl = struct.unpack("<I", cpu.mem_read(0x18818504, 4))[0]
    receipt = struct.unpack("<16I", cpu.mem_read(RESTORE_RECEIPT & 0x1FFFFFFF, 64))

    assert pc == kernel_entry, f"expected pc={hex(kernel_entry)} got {hex(pc)}"
    assert a0 == 0xFFFFFFFE and a1 == dtb_address and a2 == 0 and a3 == 0
    assert wdt_ctrl == 0, f"watchdog control not cleared: {hex(wdt_ctrl)}"
    assert wdt_writes == [(0x18818504, 4, 0)], f"unexpected watchdog writes: {wdt_writes}"
    assert receipt[0] == RELEASE_MAGIC and receipt[2] == tag
    assert receipt[3] == 0 and receipt[7] == 6 and receipt[8] == kernel_entry
    assert receipt[9] == dtb_address and receipt[10] == 0

    return {
        "status": "PASS",
        "pc": hex(pc),
        "uhi_a0": hex(a0),
        "uhi_a1_dtb": hex(a1),
        "wdt_ctrl_after": wdt_ctrl,
        "receipt_magic": hex(receipt[0]),
        "watchdog_seconds": receipt[10],
    }


def build_release_candidate(profile: Path, out: Path) -> dict:
    if out.exists() or not out.parent.is_dir():
        raise ValueError("output must be new, with an existing parent")
    kernel_manifest = json.loads((profile / "manifest.json").read_text())
    image = (profile / "vmlinux.bin").read_bytes()
    dtb = (profile / "r36-lab.dtb").read_bytes()
    for name, data in (("vmlinux.bin", image), ("r36-lab.dtb", dtb)):
        assert hashlib.sha256(data).hexdigest() == kernel_manifest["sha256"][name]
    config = (profile / "kernel.config").read_text()
    assert "CONFIG_PAGE_SIZE_4KB=y" in config
    memories = [p for p in properties(dtb).values() if p.get("device_type") == b"memory\0"]
    assert len(memories) == 1
    start, size = struct.unpack(">II", memories[0]["reg"])
    receipt_phys = RESTORE_RECEIPT & 0x1FFFFFFF
    assert start == 0 and size // 4096 * 4096 == 0x02F91000
    assert receipt_phys + 64 <= size <= 0x02F92000

    stock = (ROOT / "analysis/boot_crypto/original_advapi32.dll").read_bytes()
    assert hashlib.md5(stock).hexdigest() == "3510ffdfd039f850345ace1489572659"
    loader_source = (ROOT / "analysis/card2_files/kdump/tpl_decrypted.bin").read_bytes()
    loader, key = unpack_loader(loader_source), recover_key(loader_source)
    stock_header = parse_uimage(decrypt(stock, key))

    load, entry = int(kernel_manifest["load"], 0), int(kernel_manifest["entry"], 0)
    memory_size = (kernel_manifest["memsz"] + 4095) & ~4095
    dtb_address = load + memory_size
    tag = int.from_bytes(secrets.token_bytes(4), "little")

    code = make_release_shim(SHIM, entry, dtb_address, tag)
    assert SHIM + len(code) < load

    payload = bytes(SHIM - 0x80000000) + code
    payload += bytes(load - 0x80000000 - len(payload))
    payload += image + bytes(memory_size - len(image)) + dtb
    assert payload[:4] == bytes(4)

    plain = make_uimage(payload, 0x80000000, SHIM, timestamp=stock_header["timestamp"])
    if len(plain) > len(stock) - 16:
        raise ValueError(f"release candidate ({len(plain)} B) exceeds stock slot ({len(stock) - 16} B)")
    plain += bytes(len(stock) - 16 - len(plain))
    wrapped = encrypt(plain, key, secrets.token_bytes(12))
    assert len(wrapped) == len(stock) and decrypt(wrapped, key) == plain
    assert gzip.decompress(plain[64:]) == payload

    native = validate(loader, plain, inflate=True)
    assert native["return_code"] == 0 and int(native["entry"], 0) == SHIM

    record = {
        "mode": "permanent_release",
        "watchdog_seconds": 0,
        "deployed": False,
        "hardware_verified": False,
        "kernel": "custom Linux " + kernel_manifest["release"],
        "custom_kernel": True,
        "original_entry": hex(entry),
        "probe_entry": hex(SHIM),
        "probe_bytes": len(code),
        "session_tag": hex(tag),
        "sha256": hashlib.sha256(wrapped).hexdigest(),
        "compressed_uimage_bytes": len(make_uimage(payload, 0x80000000, SHIM, timestamp=stock_header["timestamp"])),
        "slot_capacity_bytes": len(stock) - 16,
        "source_kernel_sha256": kernel_manifest["sha256"]["vmlinux.bin"],
        "source_dtb_sha256": kernel_manifest["sha256"]["r36-lab.dtb"],
        "source_release": kernel_manifest["release"],
        "inline_dtb": hex(dtb_address),
        "source_profile": str(profile),
        "restore_receipt_phys": hex(receipt_phys),
        "native_loader_image_and_gzip": native,
        "normal_path": "NOR -> native decrypt/gzip -> release shim (WDT off, zero SD writes) -> Linux 7.2",
        "rollback_path": "Copy backed-up original advapi32.dll back to /cubegm/advapi32.dll on SD card",
        "hardware_scope_warning": "HC16E310 (128 MiB RAM) ONLY — do not flash on RK3326 or 256 MiB GB350 units",
    }
    out.mkdir()
    (out / "advapi32.dll.release.NOT_DEPLOYED").write_bytes(wrapped)
    (out / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")

    emu = emulate_release_candidate(out)
    record["unicorn_emulation"] = emu
    (out / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args()
    record = build_release_candidate(args.profile, args.out)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
