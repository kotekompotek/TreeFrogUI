# Installing & Rolling Back Linux 7.2 on R36S Clone (HiChip HC16E310)

> [!CAUTION]
> **HARDWARE COMPATIBILITY — HiChip HC16E310 (128 MiB RAM) ONLY!**
> This port has been tested **exclusively** on a single R36S-clone / SF3000-family unit running **HiChip HC16E310 (MIPS32 74Kf, 128 MiB RAM)** with stock `advapi32.dll` (`MD5: 3510ffdfd039f850345ace1489572659`).
> **Do NOT install** on Rockchip RK3326 (original R36S), Allwinner boards, or 256 MiB GB350 revisions.

---

## 1. Mandatory Verification & Backup

1. Power off the handheld and insert the microSD card into a PC card reader.
2. Locate `cubegm/advapi32.dll` on the SD card and verify its MD5 matches `3510ffdfd039f850345ace1489572659`.
3. **Back up the original `advapi32.dll` to your PC AND keep a copy as `cubegm/advapi32.dll.stock` on the SD card.**

---

## 2. Copy Runtime Files to SD Card

Copy everything from the release `cubegm/` folder into `/cubegm/` on the SD card:

- `driver_r36_combined.so` (unified DRM + ALSA video/audio backend, includes `pico286` 0-arg audio fix)
- `r36_hc16xx_drm.ko` (DRM/KMS display kernel module)
- `r36_hc16xx_i2s.ko` (I2S audio kernel module)
- `r36-sysd` (backlight, volume, GPIO15/19 PA/HP-detect, ADC battery & power daemon)
- `r36-legacy-keys` + `evdev-to-legacy.map` (15-button input bridge to `/tmp/joy_key`)
- `r36-tfkey` (`r36-tfkey dump` button diagnostic tool)
- `fsck.fat` (automatic dirty-FAT32 self-repair when SD mounts read-only after power loss)
- `modules.tar.gz` (optional Wi-Fi/BT/USB host modules)

### BIOS & Emulator Notes

- **GBA:** Place `gba_bios.bin` in `/cubegm/bios/` (or `/cubegm/lib/`). Requests for `gpsp_multicore_libretro.so` are automatically redirected by `r36_session_init` to verified `gpsp_libretro.so` (`942/942` GBA PASS).
- **Arcade NeoGeo / PGM:** Copy `neogeo.zip` and `pgm.zip` from `/cubegm/cores/bios/` directly into the arcade ROM directory (`/roms/MAME/` or `/MAME/`) so `fbalpha2012_neogeo_libretro.so` can load NeoGeo games.
- **PS1:** Use `pcsx_rearmed_libretro.so` via `picoarch_hi` (default in TreeFrogUI, `10/10` PASS). Legacy standalone `pcsx4all` requires `/dev/fb0` and is not supported.
- **Mega Drive:** For edge-case titles such as `tribe.bin` that crash `picodrive_libretro.so`, switch the core to `genesis_plus_gx_libretro.so`.

---

## 3. Safe Two-Stage Install

### Stage A — 90-Second Auto-Restoring Trial (Required First Step)
1. Copy your original `advapi32.dll` to `cubegm/R36STOCK.ENC`.
2. Copy `boot_images/trial_watchdog90/advapi32.dll` over `cubegm/advapi32.dll`.
3. Boot the console: the shim automatically restores stock `advapi32.dll` before entering Linux 7.2 and arms a 90-second watchdog so you can verify display, audio, buttons, and game launches before it cleanly reboots to stock.

### Stage B — Permanent Install (Only After Stage A Passes on Your Unit)
1. Copy `boot_images/permanent_release/advapi32.dll` over `cubegm/advapi32.dll`.
2. This release image disables the hardware watchdog and performs **zero SD writes** during NOR boot (eliminating power-loss FAT corruption risk).

---

## 4. One-Step Rollback to Stock

1. Power off the console and insert the microSD card into a PC.
2. Copy your backed-up `advapi32.dll.stock` back to `cubegm/advapi32.dll`.
3. Reinsert the SD card — stock firmware boots normally.
