#!/bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pavel Kotek
# Build tfview (PC screen stream viewer + button sender) for the console.
# glibc 2.20 dynamic, because it dlopen()s the console's display driver.
#   ZIG=/path/to/zig ./build.sh   ->  ../tfview
set -eu
cd "$(dirname "$0")"
ZIG=${ZIG:-zig}
"$ZIG" cc -target mipsel-linux-gnueabihf.2.20 -mcpu=mips32r2 -O2 -s -Wall -Wextra -Wno-unused-function \
    -o ../tfview tfview.c ../capture/tfcodec.c -ldl -lm
ls -l ../tfview
