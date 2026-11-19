"""Assemble and verify a complete Linux 7.2 release bundle for HC16E310 (128 MiB RAM).

Outputs a self-contained directory + optional .zip containing:
  - cubegm/ overlay files (driver_r36_combined.so, r36_hc16xx_drm.ko, r36_hc16xx_i2s.ko,
    r36-sysd, r36-legacy-keys, evdev-to-legacy.map, r36-tfkey, fsck.fat, modules.tar.gz)
  - boot_images/trial_watchdog90/advapi32.dll  (safe 90s auto-restoring trial image)
  - boot_images/permanent_release/advapi32.dll (zero-watchdog, zero-SD-write release image)
  - INSTALL.md, INSTALL.ru.md, RELEASE_MANIFEST.json (with SHA256 of every file)
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_HARDWARE = {
    "soc": "HiChip HC16E310",
    "ram_mib": 128,
    "stock_advapi32_md5": "3510ffdfd039f850345ace1489572659",
    "warning": "TESTED ONLY ON HICHIP HC16E310 (128 MiB). Do NOT install on RK3326 or 256 MiB GB350 units.",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_mips_elf(path: Path) -> None:
    hdr = path.read_bytes()[:20]
    if len(hdr) < 20 or hdr[:4] != b"\x7fELF" or hdr[4] != 1 or hdr[5] != 1:
        raise ValueError(f"{path} is not a 32-bit little-endian ELF")
    e_machine = int.from_bytes(hdr[18:20], "little")
    if e_machine != 8:  # EM_MIPS
        raise ValueError(f"{path} ELF e_machine={e_machine}, expected EM_MIPS (8)")


def verify_legacy_keymap(path: Path) -> int:
    raw = path.read_bytes()
    if b"\r" in raw:
        raise ValueError(f"{path} contains CRLF; must be LF-only")
    lines = [ln.strip() for ln in raw.decode("ascii").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) < 12:
        raise ValueError(f"{path} has only {len(lines)} mappings; expected >= 12")
    return len(lines)


def package_release(
    *,
    kernel_profile: Path,
    trial_dir: Path,
    release_dir: Path,
    initramfs_dir: Path,
    driver_so: Path,
    keymap_file: Path,
    out_dir: Path,
    fsck_fat: Path | None = None,
    zip_out: Path | None = None,
    version: str = "linux7.2-hc16e310-rc1",
) -> dict:
    if out_dir.exists():
        raise ValueError(f"out_dir already exists: {out_dir}")

    k_man = json.loads((kernel_profile / "manifest.json").read_text())
    t_man = json.loads((trial_dir / "manifest.json").read_text())
    r_man = json.loads((release_dir / "manifest.json").read_text())

    if r_man.get("mode") != "permanent_release" or r_man.get("watchdog_seconds") != 0:
        raise ValueError("release_dir manifest must be permanent_release with watchdog_seconds=0")
    if r_man.get("unicorn_emulation", {}).get("status") != "PASS":
        raise ValueError("release_dir must have unicorn_emulation.status == PASS")
    if t_man.get("source_kernel_sha256") != k_man["sha256"]["vmlinux.bin"]:
        raise ValueError("trial_dir kernel SHA256 mismatch with kernel_profile")
    if r_man.get("source_kernel_sha256") != k_man["sha256"]["vmlinux.bin"]:
        raise ValueError("release_dir kernel SHA256 mismatch with kernel_profile")

    verify_mips_elf(driver_so)
    keymap_count = verify_legacy_keymap(keymap_file)

    bins = initramfs_dir / "bins/sbin"
    cubegm_sources = {
        "cubegm/driver_r36_combined.so": driver_so,
        "cubegm/r36_hc16xx_drm.ko": kernel_profile / "r36_hc16xx_drm.ko",
        "cubegm/r36_hc16xx_i2s.ko": kernel_profile / "r36_hc16xx_i2s.ko",
        "cubegm/modules.tar.gz": kernel_profile / "modules.tar.gz",
        "cubegm/r36-sysd": bins / "r36-sysd",
        "cubegm/r36-legacy-keys": bins / "r36-legacy-keys",
        "cubegm/r36-tfkey": bins / "r36-tfkey",
        "cubegm/fsck.fat": fsck_fat if fsck_fat is not None else (bins / "fsck.fat"),
        "cubegm/evdev-to-legacy.map": keymap_file,
    }
    boot_sources = {
        "boot_images/trial_watchdog90/advapi32.dll": trial_dir / "advapi32.dll.encrypted.NOT_DEPLOYED",
        "boot_images/permanent_release/advapi32.dll": release_dir / "advapi32.dll.release.NOT_DEPLOYED",
    }

    for rel, src in {**cubegm_sources, **boot_sources}.items():
        if not src.is_file():
            raise FileNotFoundError(f"missing required artifact for {rel}: {src}")

    for mips_key in ("cubegm/r36-sysd", "cubegm/r36-legacy-keys", "cubegm/r36-tfkey", "cubegm/fsck.fat"):
        verify_mips_elf(cubegm_sources[mips_key])

    out_dir.mkdir(parents=True)
    file_hashes = {}
    for rel, src in {**cubegm_sources, **boot_sources}.items():
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        file_hashes[rel] = {"bytes": dst.stat().st_size, "sha256": sha256_file(dst)}

    # Verify copied advapi32.dll hashes match manifests
    assert file_hashes["boot_images/trial_watchdog90/advapi32.dll"]["sha256"] == t_man["sha256"]
    assert file_hashes["boot_images/permanent_release/advapi32.dll"]["sha256"] == r_man["sha256"]

    # Copy optional console helpers (power settings, hw diag script, PC installer) if present
    opt_files = {
        "cubegm/r36-power-settings": bins / "r36-power-settings",
        "cubegm/r36-hw-diag.sh": ROOT / "scripts/peripheral_lab/r36-hw-diag.sh",
        "install_to_sd.py": ROOT / "scripts/peripheral_lab/install_to_sd.py",
    }
    for rel, opt_src in opt_files.items():
        if opt_src.is_file():
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(opt_src, dst)
            file_hashes[rel] = {"bytes": dst.stat().st_size, "sha256": sha256_file(dst)}

    # Copy user-facing docs if present in repo
    for doc_name in ("INSTALL.md", "INSTALL.ru.md", "CONSOLE_EMULATOR.md"):
        doc_src = ROOT / doc_name
        if doc_src.is_file():
            dst = out_dir / doc_name
            shutil.copy2(doc_src, dst)
            file_hashes[doc_name] = {"bytes": dst.stat().st_size, "sha256": sha256_file(dst)}

    manifest = {
        "version": version,
        "hardware_requirements": REQUIRED_HARDWARE,
        "kernel_release": k_man.get("release"),
        "kernel_build_version": k_man.get("build_version"),
        "trial_watchdog_seconds": t_man.get("watchdog_seconds"),
        "release_watchdog_seconds": r_man.get("watchdog_seconds"),
        "keymap_entries": keymap_count,
        "files": file_hashes,
        "hardware_acceptance_required_before_public_flash": True,
    }
    (out_dir / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if zip_out is not None:
        zip_out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.rglob("*")):
                if p.is_file():
                    zf.write(p, arcname=p.relative_to(out_dir).as_posix())
        manifest["zip_archive"] = {"path": str(zip_out), "bytes": zip_out.stat().st_size, "sha256": sha256_file(zip_out)}

    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kernel-profile", type=Path, required=True)
    p.add_argument("--trial-dir", type=Path, required=True)
    p.add_argument("--release-dir", type=Path, required=True)
    p.add_argument("--initramfs-dir", type=Path, required=True)
    p.add_argument("--driver-so", type=Path, required=True)
    p.add_argument("--keymap", type=Path, required=True)
    p.add_argument("--fsck-fat", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--zip", type=Path, default=None)
    p.add_argument("--version", default="linux7.2-hc16e310-rc1")
    args = p.parse_args()
    res = package_release(
        kernel_profile=args.kernel_profile,
        trial_dir=args.trial_dir,
        release_dir=args.release_dir,
        initramfs_dir=args.initramfs_dir,
        driver_so=args.driver_so,
        keymap_file=args.keymap,
        fsck_fat=args.fsck_fat,
        out_dir=args.out,
        zip_out=args.zip,
        version=args.version,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
