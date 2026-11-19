"""Unit tests for the safe HC16E310 SD card installer & rollback tool."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

LAB = Path(__file__).resolve().parent
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

import install_to_sd as inst  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_install_trial_permanent_rollback_and_board_guard(tmp_path, monkeypatch):
    stock_bytes = b"STOCK_HC16E310_ADVAPI32"
    monkeypatch.setattr(inst, "STOCK_ADVAPI32_MD5", hashlib.md5(stock_bytes).hexdigest())

    # 1. Build a synthetic bundle zip
    bundle_dir = tmp_path / "bundle_src"
    (bundle_dir / "cubegm").mkdir(parents=True)
    (bundle_dir / "boot_images/trial_watchdog90").mkdir(parents=True)
    (bundle_dir / "boot_images/permanent_release").mkdir(parents=True)

    drv_bytes = b"DRIVER_V2"
    trial_bytes = b"TRIAL_ADVAPI32"
    perm_bytes = b"PERM_ADVAPI32"
    (bundle_dir / "cubegm/driver_r36_combined.so").write_bytes(drv_bytes)
    (bundle_dir / "boot_images/trial_watchdog90/advapi32.dll").write_bytes(trial_bytes)
    (bundle_dir / "boot_images/permanent_release/advapi32.dll").write_bytes(perm_bytes)
    (bundle_dir / "RELEASE_MANIFEST.json").write_text(json.dumps({
        "version": "test-v45",
        "files": {
            "cubegm/driver_r36_combined.so": {"bytes": len(drv_bytes), "sha256": _sha256(drv_bytes)},
            "boot_images/trial_watchdog90/advapi32.dll": {"bytes": len(trial_bytes), "sha256": _sha256(trial_bytes)},
            "boot_images/permanent_release/advapi32.dll": {"bytes": len(perm_bytes), "sha256": _sha256(perm_bytes)},
        },
    }))
    bundle_zip = tmp_path / "bundle.zip"
    with zipfile.ZipFile(bundle_zip, "w") as zf:
        for p in sorted(bundle_dir.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=p.relative_to(bundle_dir).as_posix())

    # 2. Reject incompatible board (wrong advapi32.dll MD5)
    bad_sd = tmp_path / "bad_sd"
    (bad_sd / "cubegm").mkdir(parents=True)
    (bad_sd / "cubegm/advapi32.dll").write_bytes(b"RK3326_OR_GB350_WRONG")
    with pytest.raises(RuntimeError, match="Incompatible"):
        inst.install_to_sd(bad_sd, bundle_zip, "trial")

    # 3. Valid HC16E310 SD -> install trial -> upgrade permanent -> rollback to stock
    sd = tmp_path / "good_sd"
    (sd / "cubegm/cores/bios").mkdir(parents=True)
    (sd / "roms/MAME").mkdir(parents=True)
    (sd / "cubegm/advapi32.dll").write_bytes(stock_bytes)
    (sd / "cubegm/cores/bios/neogeo.zip").write_bytes(b"NEOGEO_BIOS")
    pc_bak = tmp_path / "pc_backup"

    res_trial = inst.install_to_sd(sd, bundle_zip, "trial", pc_bak)
    assert res_trial["installed_advapi32_sha256"] == _sha256(trial_bytes)
    assert (sd / "cubegm/advapi32.dll").read_bytes() == trial_bytes
    assert (sd / "cubegm/advapi32.dll.stock").read_bytes() == stock_bytes
    assert (sd / "cubegm/R36STOCK.ENC").read_bytes() == stock_bytes
    assert (pc_bak / "advapi32.dll.stock").read_bytes() == stock_bytes
    assert (sd / "roms/MAME/neogeo.zip").read_bytes() == b"NEOGEO_BIOS"

    res_perm = inst.install_to_sd(sd, bundle_zip, "permanent")
    assert res_perm["installed_advapi32_sha256"] == _sha256(perm_bytes)
    assert (sd / "cubegm/advapi32.dll").read_bytes() == perm_bytes

    res_rb = inst.install_to_sd(sd, None, "rollback")
    assert res_rb["mode"] == "rollback"
    assert (sd / "cubegm/advapi32.dll").read_bytes() == stock_bytes
