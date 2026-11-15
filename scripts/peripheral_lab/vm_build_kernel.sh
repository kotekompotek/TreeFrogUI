#!/bin/bash
set -euo pipefail
ROOT=/work/project
REV=da5f1a22ef2ff5c46aa3f750fa10825813970b09
SRC=/work/linux-hichip-$REV
PROFILE=${R36_BUILD_PROFILE:-avp}
case "$PROFILE" in avp|display|usb) ;; *) exit 22 ;; esac
OUT=/work/kernel-$PROFILE-build
status=/work/kernel-build.exit
trap 'code=$?; printf "%s\n" "$code" > "$status"; sync' EXIT
mkdir -p "$OUT"
apk add --no-progress findutils texinfo
if [ ! -x /work/cross/bin/mipsel-linux-gnu-as ]; then
    GAS_SHA=1d8688f1b6f1bc64cfd1f82e3af05b8ace1d709d4fa819acb4d12d74e1b69b4314d98fb4281dacc9b5fa51ff7370d0249f540ec016fd137aa701502d72426301
    curl -fL --retry 2 -o /work/binutils-with-gold-2.44.tar.xz https://ftp.gnu.org/gnu/binutils/binutils-with-gold-2.44.tar.xz
    printf '%s  %s\n' "$GAS_SHA" /work/binutils-with-gold-2.44.tar.xz | sha512sum -c -
    tar -xJf /work/binutils-with-gold-2.44.tar.xz -C /work
    mkdir -p /work/build-gas
    (cd /work/build-gas && /work/binutils-with-gold-2.44/configure --target=mipsel-linux-gnu \
        --prefix=/work/cross --disable-nls --disable-werror --disable-gdb --disable-gdbserver \
        --disable-gprofng --disable-gold --disable-binutils --disable-ld --disable-sim \
        --disable-shared --enable-static && make -j2 MAKEINFO=true all-gas && make MAKEINFO=true install-gas)
fi
export PATH=/work/cross/bin:$PATH
MAKE_ARGS=(ARCH=mips LLVM=1 LLVM_IAS=0 CROSS_COMPILE=/work/cross/bin/mipsel-linux-gnu-)
if [ ! -d "$SRC" ]; then
    curl -fL --retry 2 -o /work/kernel-source.tar.gz "https://codeload.github.com/SiarheiVolkau/linux-hichip/tar.gz/$REV"
    sha256sum /work/kernel-source.tar.gz > /work/kernel-source.sha256
    tar -xzf /work/kernel-source.tar.gz -C /work
fi
python3 "$ROOT/scripts/kernel_lab/integrate_ports.py" "$SRC"
cp "$ROOT/base/kernel.config" "$SRC/.config"
cp "$ROOT/scripts/kernel_lab/r36-lab.dts" "$SRC/arch/mips/boot/dts/hichip/r36-base.dts"
cp "$ROOT/scripts/kernel_lab/r36-boot.dts" "$SRC/arch/mips/boot/dts/hichip/r36-boot.dts"
cp "$ROOT/scripts/kernel_lab/r36-avp-poll.dts" "$SRC/arch/mips/boot/dts/hichip/r36-lab.dts"
if [ "$PROFILE" = usb ]; then
    cp "$ROOT/scripts/kernel_lab/r36-avp-poll.dts" "$SRC/arch/mips/boot/dts/hichip/r36-avp-poll.dts"
    cp "$ROOT/scripts/kernel_lab/r36-usb-cdc.dts" "$SRC/arch/mips/boot/dts/hichip/r36-lab.dts"
fi
if [ "$PROFILE" = display ]; then
    cp "$ROOT/scripts/kernel_lab/r36-avp-poll.dts" "$SRC/arch/mips/boot/dts/hichip/r36-avp-poll.dts"
    cp "$ROOT/display_driver/r36-display.dts" "$SRC/arch/mips/boot/dts/hichip/r36-lab.dts"
    if [ "${R36_INPUT_PROBE:-0}" = 1 ]; then
        cp "$ROOT/display_driver/r36-display.dts" "$SRC/arch/mips/boot/dts/hichip/r36-display.dts"
        cp "$ROOT/scripts/kernel_lab/r36-display-input.dts" "$SRC/arch/mips/boot/dts/hichip/r36-lab.dts"
    fi
fi
printf 'dir /dev 0755 0 0\ndir /proc 0755 0 0\ndir /sys 0755 0 0\ndir /sd 0755 0 0\ndir /tmp 1777 0 0\nfile /init %s/init.elf 0755 0 0\nnod /dev/console 0600 0 0 c 5 1\n' "$ROOT" > "$ROOT/initramfs.list"
"$SRC/scripts/config" --file "$SRC/.config" --set-str LOCALVERSION -r36port \
    --disable LOCALVERSION_AUTO --set-str INITRAMFS_SOURCE "$ROOT/initramfs.list" \
    --enable SYSVIPC --enable SYSVIPC_SYSCTL --disable DEBUG_INFO_BTF --disable WERROR
if [ "$PROFILE" = display ]; then
    mkdir -p "$SRC/drivers/gpu/drm/r36_hc16xx"
    cp "$ROOT/display_driver/Kconfig" "$SRC/drivers/gpu/drm/r36_hc16xx/Kconfig"
    grep -qxF 'source "drivers/gpu/drm/r36_hc16xx/Kconfig"' "$SRC/drivers/gpu/drm/Kconfig" || printf '\nsource "drivers/gpu/drm/r36_hc16xx/Kconfig"\n' >> "$SRC/drivers/gpu/drm/Kconfig"
    "$SRC/scripts/config" --file "$SRC/.config" --set-str LOCALVERSION -r36disp \
        --enable DRM_R36_HC16XX_DEPS \
        --enable DRM --enable DRM_KMS_HELPER --enable DRM_GEM_DMA_HELPER \
        --enable VIDEOMODE_HELPERS --enable OF_VIDEOMODE --enable OF_DISPLAY_TIMING \
        --enable APERTURE_HELPERS --disable DRM_FBDEV_EMULATION
fi
if [ "$PROFILE" = usb ]; then
    "$SRC/scripts/config" --file "$SRC/.config" --set-str LOCALVERSION -r36usb \
        --enable USB --enable USB_GADGET --enable USB_MUSB_HDRC --enable USB_MUSB_HC16XX \
        --disable USB_MUSB_DUAL_ROLE --disable USB_MUSB_HOST --enable USB_MUSB_GADGET \
        --enable MUSB_PIO_ONLY --enable PHY_HICHIP_USB \
        --enable USB_CONFIGFS --enable USB_CONFIGFS_ACM --enable PRINTK_TIME \
        --enable EXPERT --disable VT --disable VT_CONSOLE \
        --disable HID_SUPPORT --disable HID --disable USB_HID \
        --disable USB_KBD --disable USB_MOUSE --disable USB_HIDDEV \
        --disable INPUT --disable GPIO_HC16XX --disable PINCTRL_HC16XX \
        --disable SOUND --disable SND --disable DRM --disable DRM_R36_HC16XX_DEPS
fi
if [ "${R36_INPUT_PROBE:-0}" = 1 ]; then
    "$SRC/scripts/config" --file "$SRC/.config" \
        --enable GPIOLIB --enable GPIO_HC16XX --enable PINCTRL --enable PINCTRL_HC16XX \
        --enable INPUT --enable INPUT_EVDEV --enable INPUT_KEYBOARD \
        --enable KEYBOARD_GPIO_POLLED --enable KEYBOARD_GPIO_SERIALIZER
fi
if [ "${R36_AUDIO_BUILD:-0}" = 1 ]; then
    # SND_PCM is a hidden Kconfig symbol: scripts/config --enable alone is
    # discarded by olddefconfig. A visible dependency option must select it.
    mkdir -p "$SRC/sound/r36-lab"
    printf 'config SND_R36_EXTERNAL_DEPS\n\tbool "R36 external native PCM dependencies"\n\tdepends on SND && OF && HAS_DMA\n\tselect SND_PCM\n' > "$SRC/sound/r36-lab/Kconfig"
    grep -qxF 'source "sound/r36-lab/Kconfig"' "$SRC/sound/Kconfig" || printf '\nsource "sound/r36-lab/Kconfig"\n' >> "$SRC/sound/Kconfig"
    "$SRC/scripts/config" --file "$SRC/.config" --enable SOUND --enable SND --enable SND_R36_EXTERNAL_DEPS --enable SND_PROC_FS
    # The native audio node stays disabled. Compiling never transfers ownership.
    printf '\n#include "r36-audio.dts"\n' >> "$SRC/arch/mips/boot/dts/hichip/r36-lab.dts"
    cp "$ROOT/audio_driver/r36-audio.dts" "$SRC/arch/mips/boot/dts/hichip/r36-audio.dts"
fi
make -C "$SRC" "${MAKE_ARGS[@]}" olddefconfig
if [ "$PROFILE" = usb ]; then
    for option in INPUT GPIO_HC16XX SND DRM VT USB_MUSB_HOST USB_MUSB_DUAL_ROLE; do
        if grep -qE "^CONFIG_${option}=[ym]$" "$SRC/.config"; then
            printf 'USB isolation failed: %s\n' "$option" >&2
            exit 54
        fi
    done
fi
if [ "${R36_AUDIO_BUILD:-0}" = 1 ]; then
    grep -qxF 'CONFIG_SND_PCM=y' "$SRC/.config"
    grep -qxF 'CONFIG_SND_R36_EXTERNAL_DEPS=y' "$SRC/.config"
fi
make -C "$SRC" -j1 "${MAKE_ARGS[@]}" vmlinux hichip/r36-lab.dtb
make -C "$SRC" "${MAKE_ARGS[@]}" modules_prepare
cp "$SRC/vmlinux.symvers" "$SRC/Module.symvers"
# A previous abrupt VM stop can leave zero-length objects with valid timestamps.
# Never reuse external module intermediates from an earlier invocation.
for module_dir in "$ROOT/scripts/kernel_lab/amprpc_driver" "$ROOT/scripts/kernel_lab/hello_driver"; do
    make -C "$SRC" "${MAKE_ARGS[@]}" M="$module_dir" clean
done
if [ "$PROFILE" = display ]; then
    make -C "$SRC" "${MAKE_ARGS[@]}" M="$ROOT/display_driver" clean
fi
make -C "$SRC" "${MAKE_ARGS[@]}" M="$ROOT/scripts/kernel_lab/amprpc_driver" modules
make -C "$SRC" "${MAKE_ARGS[@]}" M="$ROOT/scripts/kernel_lab/hello_driver" modules
if [ "$PROFILE" = display ]; then
    make -C "$SRC" "${MAKE_ARGS[@]}" M="$ROOT/display_driver" modules
fi
if [ "${R36_AUDIO_BUILD:-0}" = 1 ]; then
    make -C "$SRC" "${MAKE_ARGS[@]}" M="$ROOT/audio_driver" clean
    make -C "$SRC" "${MAKE_ARGS[@]}" M="$ROOT/audio_driver" modules
fi
llvm-objcopy -O binary "$SRC/vmlinux" "$OUT/vmlinux.bin"
cp "$SRC/vmlinux" "$OUT/vmlinux.elf"
cp "$SRC/arch/mips/boot/dts/hichip/r36-lab.dtb" "$OUT/r36-lab.dtb"
cp "$SRC/.config" "$OUT/kernel.config"
cp "$SRC/System.map" "$OUT/System.map"
cp "$ROOT/init.elf" "$OUT/init.elf"
cp "$SRC/usr/initramfs_inc_data" "$OUT/initramfs.cpio.gz"
cp "$ROOT/scripts/kernel_lab/amprpc_driver/r36_amprpc_poll.ko" "$OUT/"
cp "$ROOT/scripts/kernel_lab/hello_driver/r36hello.ko" "$OUT/"
if [ "$PROFILE" = display ]; then
    cp "$ROOT/display_driver/r36_hc16xx_drm.ko" "$ROOT/display_driver/port_source.json" "$OUT/"
fi
if [ "${R36_AUDIO_BUILD:-0}" = 1 ]; then
    cp "$ROOT/audio_driver/r36_hc16xx_i2s.ko" "$OUT/"
fi
python3 "$ROOT/scripts/kernel_lab/package_kernel.py" "$OUT" "$REV" "$PROFILE" "$SRC"
tar -C "$OUT" -czf /work/kernel-$PROFILE-build.tar.gz .
test -s /work/kernel-$PROFILE-build.tar.gz
gzip -t /work/kernel-$PROFILE-build.tar.gz
sync
echo R36_KERNEL_BUILD_COMPLETE
