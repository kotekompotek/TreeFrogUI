# R36S Clone (HC16E310) — Linux 7.2 Port & Peripheral Stack

> [!IMPORTANT]
> **Hardware Testing Scope:** All hardware tests and cold NOR boot trials in this repository were performed **exclusively on the HiChip HC16E310 processor** (on a single R36S-clone / SF3000-family unit). Other SoCs, board revisions, and hardware variants have **not** been tested.

## Overview

This repository contains the Linux `7.2.0-rc5` port, out-of-tree peripheral drivers, userspace daemons, and verification tooling for the HC16E310 handheld console:

- **Kernel (`PROFILE=full`, `7.2.0-rc5-r36full`):** `scripts/kernel_lab/r36-full.dts`, `scripts/peripheral_lab/vm_build_kernel.sh` (`CONFIG_CC_OPTIMIZE_FOR_SIZE=y`, dual MUSB USB0/USB1, `hc16xx-gpio`, `r36-direct-keys` + `r36-serial-keys`, PWM backlight, SAR ADC, Wi-Fi/BT `.ko` modules).
- **Display & Audio Backend:** `scripts/driver_port/driver_r36_combined_backend.c` (`driver_r36_combined_v1.so` MIPS32r2, `RTLD_NOW` `dlopen` verified under `qemu-mipsel` against console runtime).
- **System Daemon & Power Settings:** `scripts/peripheral_lab/r36_sysd.c`, `r36_sysd_conf.h`, `r36_power_settings.c` (volume/brightness persistence, PA/HP-detect policy, smooth 5s fade before screen-off, auto-poweroff, `/dev/fb0` settings UI, clean `RB_POWER_OFF`).
- **Session Supervisor & Recovery:** `scripts/peripheral_lab/r36_session_init.c`, `scripts/peripheral_lab/prepare_session_initramfs.py`, `scripts/kernel_lab/r36_chkdsk_console.c`, `scripts/peripheral_lab/usb_mtp_adb_service.c`.
- **Current Status & Handoff:** See `AGENT_HANDOFF.ru.md`, `analysis/driver_port/UI_PORT_PLAN.ru.md`, and `analysis/driver_port/FRONTEND_PORT_STATUS.json`.

## Running Offline Tests

```bash
python -m pytest scripts -q
```
