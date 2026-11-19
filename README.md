# R36S Clone (HC16E310) — Linux 7.2 Port, Peripheral Stack & Console Emulator

> [!IMPORTANT]
> **Hardware Testing Scope:** All hardware tests and cold NOR boot trials in this repository were performed **exclusively on the HiChip HC16E310 processor** (on a single R36S-clone / SF3000-family unit). Other SoCs, board revisions, and hardware variants have **not** been tested.

## Highlights & Current Achievements

### Hardware-Verified on R36S (`7.2.0-rc5-r36full`, trials `v1`–`v42`)
- **Direct Cold NOR Boot & Safe Auto-Restore:** Bootloader shim decrypts, restores stock `advapi32.dll` on SD with CRC32 verification before jumping directly into Linux `7.2.0-rc5-r36full`, and automatically falls back to stock Linux 4.4 / MTP via hardware watchdog (`analysis/boot_crypto/COLD_BOOT.ru.md`).
- **Display & TreeFrogUI (`640x480`):** Out-of-tree `r36_hc16xx_drm.ko` (atomic DRM/KMS + double-buffered page flip) + `driver_r36_combined_v1.so` + `picoarch` + `frogui_libretro.so` renders the live TreeFrogUI menu on the physical panel.
- **Speaker Audio (`1 kHz` Hardware-Verified):** `r36_hc16xx_i2s.ko` + direct `/dev/mem` GPIO pinmux/PA control (`L15` headphone detect, `L19` active-high mute) verified with audible 1 kHz output and PC microphone DFT peak (`sec 0: 57.4`, `sec 1: 58.3`, mute `0.1`; `v40`).
- **USB Composite FunctionFS MTP R/W + ADB Shell:** Simultaneous Windows Explorer MTP file read/write and `adb shell` over single HC16xx MUSB peripheral port (`0x18d1:0x4e22`), plus FAT32 `rw` recovery via `r36-fsck-cp437-v2`.
- **Input Bridge:** `r36-direct-keys` (`event0`) + `r36-serial-keys` (`event1`) bridged through `r36-legacy-keys` to SysV SHM (`0x61110004`, `/tmp/joy_key`), with live UI button navigation confirmed in `v42`.

### Latest Fixes Ready for Hardware Acceptance `v44` (Built & Emulated Offline)
- **Game Launching, Standalone Compatibility & Auto-Repair (`scripts/peripheral_lab/r36_session_init.c`):** Expanded launch-request line buffers from 32 to 256 bytes, fixed `picoarch` / `picoarch_hi` `<CORE_PATH> <ROM_PATH>` invocation (`gpsp|pcsx|ps1|ppsspp -> picoarch_hi`, `.sh -> /bin/sh`), exported `TF_DRIVER=`, `PATH`, `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy` (fixing `lgpt.elf`), added seamless `gpsp_multicore -> gpsp_libretro.so` fallback, and added automatic read-only FAT32 self-repair via RAM-staged `fsck.fat -a -w`.
- **Combined Driver `v2` (`scripts/peripheral_lab/audio_alsa_backend.c`):** Added 0-arg `sound_driver_init()` fallback for `pico286` (`48 kHz` stereo when `device_name != NULL` and out-of-range registers) while preserving strict `NULL`-device checks (`driver_r36_combined_v2.so`, `28 KB`, `DRIVER_CHECK=PASS`).
- **PWM Backlight & Direct Keys (`scripts/kernel_lab/r36-full.dts`, `scripts/peripheral_lab/r36_sysd.c`):** Added `pwm-backlight` (`&pwm 0 20000 0`, 20 levels, `l00`/`pwm0` pinctrl), enabled direct evdev key handling on `event0`, prevented positive brightness `%` from rounding to `raw=0`, and added `/tmp/r36-sysd.diag` + GPIO19 DIR auto-reassert.
- **Permanent Release Builder, Packager & Safe SD Installer (`scripts/boot_crypto/build_release_cold_candidate.py`, `scripts/peripheral_lab/package_release_bundle.py`, `install_to_sd.py`, `r36-hw-diag.sh`):** Zero-watchdog, zero-SD-write permanent `advapi32.dll` builder (Unicorn 74Kf verified), SHA256-verified release packager, one-command HC16E310-guarded SD installer (`--mode trial|permanent|rollback`), and 1-second ADB live-acceptance diagnostic script; see **[INSTALL.md](INSTALL.md)** / **[INSTALL.ru.md](INSTALL.ru.md)**.
- **DRM Power Settings UI (`scripts/peripheral_lab/r36_power_settings.c`):** Ported from `/dev/fb0` to `/dev/dri/card0` DRM dumb buffer (with `/dev/fb0` fallback) and R36S physical keycodes (`704..715`).
- **Kernel & Release Bundle `v45`:** Built `7.2.0-rc5-r36full #45` (`kernel_cold_full_session_v45` Unicorn `8/8` + `1/1` PASS; `kernel_release_full_session_v45` Unicorn PASS; bundled with `driver_r36_combined_v2.so`, `r36-power-settings`, `r36-hw-diag.sh`, `install_to_sd.py`, and 15-button keymap `v4`).

---

## Console Emulation & Exhaustive Emulator Verification

Full technical documentation of the 4-layer console emulation stack (Unicorn MIPS32 74Kf NOR/kernel/AMPRPC emulators, QEMU MIPS32 runtime testbed, and host hardware-mock `pytest` suite) is available in:

- **[CONSOLE_EMULATOR.md](CONSOLE_EMULATOR.md)** — Detailed architecture, memory maps, standalone emulator ABI findings, and reproduction steps.
- **[analysis/driver_port/EMULATORS_OFFLINE_v1_RESULT.json](analysis/driver_port/EMULATORS_OFFLINE_v1_RESULT.json)** — Offline `qemu-mipsel` `dlopen` audit of all `113` `.so` cores (`106` PASS, `7` FAIL), `driver_r36_combined_v1.so` (7 exports PASS), and all `7` standalone emulators (`picoarch`, `picoarch_hi`, `rockbox`, `dsperate`, `pico286`, `lgpt.elf`, `pcsx4all`).
- **[analysis/driver_port/ALL_GAMES_EMULATORS_OFFLINE_v1_RESULT.json](analysis/driver_port/ALL_GAMES_EMULATORS_OFFLINE_v1_RESULT.json)** — Exhaustive offline MIPS32 execution of **all `10,501` games** from the 16 GB SD card backup:
  - **Console & Handheld (`14` folders): `7,361 / 7,361` (100.0% PASS)** (`FC` 2907, `SFC` 2145, `GBA` 942, `PCE` 377, `MD` 342 [341 `picodrive` + `tribe.bin` on `genesis_plus_gx`], `GB` 192, `GBC` 149, `SMS` 93, `GG` 91, `WSC` 63, `NGPC` 39, `PS` 10, `ATARI` 9, `ROMS` 2).
  - **Arcade (`MAME`, `3,140` files co-located with parents + `neogeo.zip`/`pgm.zip`):** **`2,511`** verified rendering real frames (`fbneo` 2096, `mame2003_plus` 290, `fbalpha2012_neogeo` 107, `fbalpha2012_cps1` 9, `mame2000` 5, `fbalpha2012_cps2` 4); `335` hit user-mode `qemu-mipsel` `SIGBUS(10)` unaligned traps (emulated by kernel `do_ade` on real R36S hardware); `55` legacy proprietary `.fba`; `239` unresolved `.zip` romsets.
  - **Tier-A `picoarch` / `picoarch_hi` end-to-end smoke:** `22 / 28` combinations PASS (`rc=0`), `4` `qemu-mipsel` `SIGBUS(135)`, `2` `rc=255`.

---

## Repository Map

- **Kernel (`PROFILE=full`, `7.2.0-rc5-r36full`):** `scripts/kernel_lab/r36-full.dts`, `scripts/peripheral_lab/vm_build_kernel.sh`.
- **Display & Audio Backend:** `scripts/peripheral_lab/driver_r36_combined_backend.c`, `video_drm_backend.c`, `audio_alsa_backend.c` (`driver_r36_combined_v1.so`).
- **System Daemon & Power Settings:** `scripts/peripheral_lab/r36_sysd.c`, `r36_sysd_conf.h`, `r36_power_settings.c`.
- **Session Supervisor, USB & Recovery:** `scripts/peripheral_lab/r36_session_init.c`, `prepare_session_initramfs.py`, `usb_mtp_adb_service.c`, `scripts/kernel_lab/r36_chkdsk_console.c`.
- **Console Emulators & Boot Crypto:** `scripts/boot_crypto/emulate_*.py`, `scripts/kernel_lab/emulate_boot.py`, `emulate_amprpc.py`.
- **Current Handoff & Plans:** [AGENT_HANDOFF.ru.md](AGENT_HANDOFF.ru.md), [analysis/driver_port/UI_PORT_PLAN.ru.md](analysis/driver_port/UI_PORT_PLAN.ru.md), [analysis/driver_port/FRONTEND_PORT_STATUS.json](analysis/driver_port/FRONTEND_PORT_STATUS.json).

## Running Offline Tests

```bash
python -m pytest scripts -q
```

Latest verified result: **`318 passed, 14 skipped`**.
