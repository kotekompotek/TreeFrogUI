"""Safe one-command SD card installer & rollback tool for R36S HC16E310 Linux 7.2 release bundles.

Safety invariants:
  - Verifies stock advapi32.dll MD5 == 3510ffdfd039f850345ace1489572659 before touching anything
    (refuses incompatible RK3326 / Allwinner / 256 MiB GB350 units).
  - Always preserves advapi32.dll.stock and R36STOCK.ENC (+ optional PC backup).
  - Verifies SHA256 of every file copied against RELEASE_MANIFEST.json.
  - Supports --mode trial (90s auto-restore), --mode permanent (zero-watchdog), and --mode rollback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

STOCK_ADVAPI32_MD5 = "3510ffdfd039f850345ace1489572659"


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_subdir_ci(parent: Path, name: str) -> Path | None:
    low = name.lower()
    if not parent.is_dir():
        return None
    for child in parent.iterdir():
        if child.is_dir() and child.name.lower() == low:
            return child
    return None


def _ensure_stock_backup(cubegm: Path, pc_backup: Path | None) -> Path:
    adv = cubegm / "advapi32.dll"
    stock_bak = cubegm / "advapi32.dll.stock"
    r36stock = cubegm / "R36STOCK.ENC"

    if stock_bak.is_file() and md5_file(stock_bak) == STOCK_ADVAPI32_MD5:
        src_stock = stock_bak
    elif adv.is_file() and md5_file(adv) == STOCK_ADVAPI32_MD5:
        shutil.copy2(adv, stock_bak)
        assert md5_file(stock_bak) == STOCK_ADVAPI32_MD5
        src_stock = stock_bak
    else:
        got = md5_file(adv) if adv.is_file() else "MISSING"
        raise RuntimeError(
            f"Incompatible or unrecognized device! Expected stock advapi32.dll MD5 "
            f"{STOCK_ADVAPI32_MD5} (HC16E310 128 MiB), got {got}. Aborting without changes."
        )

    if not r36stock.is_file() or md5_file(r36stock) != STOCK_ADVAPI32_MD5:
        shutil.copy2(src_stock, r36stock)
        assert md5_file(r36stock) == STOCK_ADVAPI32_MD5

    if pc_backup is not None:
        pc_backup.mkdir(parents=True, exist_ok=True)
        pc_dst = pc_backup / "advapi32.dll.stock"
        if not pc_dst.is_file() or md5_file(pc_dst) != STOCK_ADVAPI32_MD5:
            shutil.copy2(src_stock, pc_dst)
            assert md5_file(pc_dst) == STOCK_ADVAPI32_MD5

    return src_stock


def _install_from_dir(sd_root: Path, bundle_dir: Path, mode: str, pc_backup: Path | None) -> dict:
    cubegm = _find_subdir_ci(sd_root, "cubegm")
    if cubegm is None:
        raise FileNotFoundError(f"cubegm directory not found under {sd_root}")

    if mode == "rollback":
        stock_bak = cubegm / "advapi32.dll.stock"
        if not stock_bak.is_file() or md5_file(stock_bak) != STOCK_ADVAPI32_MD5:
            raise RuntimeError(f"Valid stock backup not found at {stock_bak}")
        adv = cubegm / "advapi32.dll"
        shutil.copy2(stock_bak, adv)
        assert md5_file(adv) == STOCK_ADVAPI32_MD5
        return {"mode": "rollback", "restored_md5": STOCK_ADVAPI32_MD5, "target": str(adv)}

    manifest_path = bundle_dir / "RELEASE_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"RELEASE_MANIFEST.json missing in {bundle_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    _ensure_stock_backup(cubegm, pc_backup)

    copied = []
    for rel, meta in manifest["files"].items():
        if not rel.startswith("cubegm/"):
            continue
        src = bundle_dir / rel
        if not src.is_file():
            raise FileNotFoundError(f"Bundle missing {rel}")
        if sha256_file(src) != meta["sha256"]:
            raise ValueError(f"Bundle checksum mismatch for {rel}")
        dst = cubegm / rel[len("cubegm/"):]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha256_file(dst) != meta["sha256"]:
            raise IOError(f"Readback checksum mismatch on SD for {dst}")
        copied.append(rel)

    # Co-locate neogeo.zip and pgm.zip into MAME folder if present so fbalpha2012_neogeo works out of the box
    bios_copied = []
    bios_dir = cubegm / "cores" / "bios"
    mame_dir = _find_subdir_ci(sd_root, "MAME")
    if mame_dir is None:
        roms_dir = _find_subdir_ci(sd_root, "roms")
        if roms_dir is not None:
            mame_dir = _find_subdir_ci(roms_dir, "MAME")
    if bios_dir.is_dir() and mame_dir is not None:
        for bname in ("neogeo.zip", "pgm.zip"):
            bsrc = bios_dir / bname
            bdst = mame_dir / bname
            if bsrc.is_file() and not bdst.is_file():
                shutil.copy2(bsrc, bdst)
                bios_copied.append(str(bdst))

    boot_key = (
        "boot_images/trial_watchdog90/advapi32.dll"
        if mode == "trial"
        else "boot_images/permanent_release/advapi32.dll"
    )
    boot_src = bundle_dir / boot_key
    expected_sha = manifest["files"][boot_key]["sha256"]
    if sha256_file(boot_src) != expected_sha:
        raise ValueError(f"Bundle checksum mismatch for {boot_key}")
    adv_dst = cubegm / "advapi32.dll"
    shutil.copy2(boot_src, adv_dst)
    if sha256_file(adv_dst) != expected_sha:
        raise IOError("Readback checksum mismatch for installed advapi32.dll")

    return {
        "mode": mode,
        "version": manifest.get("version"),
        "installed_advapi32_sha256": expected_sha,
        "copied_cubegm_files": copied,
        "colocated_arcade_bios": bios_copied,
        "stock_backup_verified_md5": STOCK_ADVAPI32_MD5,
    }


def install_to_sd(sd_root: Path, bundle: Path | None, mode: str, pc_backup: Path | None = None) -> dict:
    if mode == "rollback":
        return _install_from_dir(sd_root, Path("."), mode, pc_backup)
    if bundle is None or not bundle.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle}")
    if bundle.is_file() and bundle.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="r36_install_") as td:
            with zipfile.ZipFile(bundle) as zf:
                zf.extractall(td)
            return _install_from_dir(sd_root, Path(td), mode, pc_backup)
    return _install_from_dir(sd_root, bundle, mode, pc_backup)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sd", type=Path, required=True, help="Mounted R36S microSD root (e.g. E:\\)")
    p.add_argument("--bundle", type=Path, default=None, help="Release bundle dir or .zip")
    p.add_argument("--mode", choices=("trial", "permanent", "rollback"), required=True)
    p.add_argument("--pc-backup", type=Path, default=None, help="Optional PC folder to store advapi32.dll.stock")
    args = p.parse_args()
    res = install_to_sd(args.sd, args.bundle, args.mode, args.pc_backup)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
