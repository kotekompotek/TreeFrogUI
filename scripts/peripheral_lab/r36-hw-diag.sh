#!/bin/sh
# One-command live hardware diagnostic script for R36S Linux 7.2 acceptance.
# Invoke via: adb shell sh /mnt/sdcard/cubegm/r36-hw-diag.sh
echo "=== UNAME ==="
uname -a
echo "=== MOUNT ==="
mount | grep -E 'sdcard|mmcblk' || true
echo "=== LSMOD ==="
lsmod 2>/dev/null || cat /proc/modules
echo "=== PS ==="
ps
echo "=== BACKLIGHT ==="
for d in /sys/class/backlight/*; do
  [ -d "$d" ] && echo "$d: br=$(cat "$d/brightness" 2>/dev/null) max=$(cat "$d/max_brightness" 2>/dev/null)"
done
echo "=== SYSD DIAG ==="
cat /tmp/r36-sysd.diag 2>/dev/null || echo "no /tmp/r36-sysd.diag"
echo "=== ADC ==="
for f in /sys/devices/platform/*/check_adc*; do
  [ -f "$f" ] && echo "$f=$(cat "$f" 2>/dev/null)"
done
echo "=== SHM & TFKEY ==="
ipcs -m 2>/dev/null || true
/mnt/sdcard/cubegm/r36-tfkey dump 2>/dev/null || echo "r36-tfkey unavailable"
echo "=== LAST GAME LOG ==="
tail -n 12 /mnt/sdcard/cubegm/logs/last_game.log 2>/dev/null || echo "no last_game.log"
echo "=== DMESG ERRORS ==="
dmesg | grep -iE 'error|fail|mmc|drm|i2s|pwm|backlight|fat' | tail -n 15
