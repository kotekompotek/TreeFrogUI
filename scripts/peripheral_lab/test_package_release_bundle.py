"""Unit tests for the HC16E310 Linux 7.2 release bundle packager."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

import pytest

LAB = Path(__file__).resolve().parent
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from package_release_bundle import package_release  # noqa: E402


def _fake_mips_elf() -> bytes:
    hdr = bytearray(64)
    hdr[0:4] = b"\x7fELF"
    hdr[4] = 1  # ELF32
    hdr[5] = 1  # little-endian
    struct.pack_into("<H", hdr, 18, 8)  # EM_MIPS
    return bytes(hdr)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_package_release_bundle_validates_and_zips(tmp_path):
    kprof = tmp_path / "kprof"
    trial = tmp_path / "trial"
    rel = tmp_path / "rel"
    initrd = tmp_path / "initrd/bins/sbin"
    for d in (kprof, trial, rel, initrd):
        d.mkdir(parents=True)

    vmlinux = b"VMLINUX_FAKE"
    vmlinux_sha = _sha256(vmlinux)
    (kprof / "manifest.json").write_text(json.dumps({
        "release": "7.2.0-rc5-r36full",
        "build_version": "#44",
        "sha256": {"vmlinux.bin": vmlinux_sha},
    }))
    for name in ("r36_hc16xx_drm.ko", "r36_hc16xx_i2s.ko", "modules.tar.gz"):
        (kprof / name).write_bytes(b"MOD_" + name.encode())

    trial_bin = b"TRIAL_ADVAPI32"
    (trial / "advapi32.dll.encrypted.NOT_DEPLOYED").write_bytes(trial_bin)
    (trial / "manifest.json").write_text(json.dumps({
        "watchdog_seconds": 90,
        "sha256": _sha256(trial_bin),
        "source_kernel_sha256": vmlinux_sha,
    }))

    rel_bin = b"RELEASE_ADVAPI32"
    (rel / "advapi32.dll.release.NOT_DEPLOYED").write_bytes(rel_bin)
    (rel / "manifest.json").write_text(json.dumps({
        "mode": "permanent_release",
        "watchdog_seconds": 0,
        "sha256": _sha256(rel_bin),
        "source_kernel_sha256": vmlinux_sha,
        "unicorn_emulation": {"status": "PASS"},
    }))

    for bname in ("r36-sysd", "r36-legacy-keys", "r36-tfkey", "fsck.fat"):
        (initrd / bname).write_bytes(_fake_mips_elf())

    drv = tmp_path / "driver.so"
    drv.write_bytes(_fake_mips_elf())

    kmap = tmp_path / "evdev-to-legacy.map"
    kmap.write_bytes(b"\n".join(f"{700+i} {i}".encode() for i in range(15)) + b"\n")

    out_dir = tmp_path / "bundle_out"
    out_zip = tmp_path / "bundle.zip"
    res = package_release(
        kernel_profile=kprof,
        trial_dir=trial,
        release_dir=rel,
        initramfs_dir=tmp_path / "initrd",
        driver_so=drv,
        keymap_file=kmap,
        out_dir=out_dir,
        zip_out=out_zip,
    )
    assert res["keymap_entries"] == 15
    assert res["trial_watchdog_seconds"] == 90
    assert res["release_watchdog_seconds"] == 0
    assert (out_dir / "RELEASE_MANIFEST.json").is_file()
    assert out_zip.is_file()
    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        assert "cubegm/driver_r36_combined.so" in names
        assert "boot_images/trial_watchdog90/advapi32.dll" in names
        assert "boot_images/permanent_release/advapi32.dll" in names
        assert "RELEASE_MANIFEST.json" in names

    # Reject CRLF keymap
    kmap_bad = tmp_path / "bad.map"
    kmap_bad.write_bytes(b"704 10\r\n" * 15)
    with pytest.raises(ValueError, match="CRLF"):
        package_release(
            kernel_profile=kprof,
            trial_dir=trial,
            release_dir=rel,
            initramfs_dir=tmp_path / "initrd",
            driver_so=drv,
            keymap_file=kmap_bad,
            out_dir=tmp_path / "bundle_bad",
        )
