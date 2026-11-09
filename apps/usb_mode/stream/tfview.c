// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pavel Kotek
/*
 * tfview - show a PC screen stream on the console and send the buttons back.
 *
 * Runs as a TreeFrogUI "standalone" app (zhijack launches it instead of the
 * menu, so it owns the display). The PC side (pc/r36stream.py) talks to it
 * through two FIFOs, bridged by one tfmtp remote job:
 *
 *   PC --(job stdin)--> /tmp/tfview.in  : frames  [ "TFV1" u32 len u16 w u16 h u8 fmt u8 pad[3] ] + payload
 *        fmt 1 = JPEG, 2 = tfcodec key frame (RGB565, lossless), 3 = tfcodec delta frame
 *   PC <--(job stdout)- /tmp/tfview.out : status  [ "TFK2" u32 keys u32 shown u32 ms ] when the buttons
 *        change, right after every displayed frame (the PC uses `shown` as an ack and keeps
 *        at most one frame in flight, so nothing queues up), and every 100 ms
 *
 * A frame packet with len 0 asks tfview to quit. Holding SELECT+START for
 * 1.5 s quits too (those two buttons still reach the PC while held briefly).
 * Frames are JPEG (decoded with stb_image) and are handed to the console's
 * display driver (video_driver_disp_frame), whose hardware scaler fills the
 * panel at any source size.
 *
 * Build: zig cc -target mipsel-linux-gnueabihf.2.20 -mcpu=mips32r2 -O2 tfview.c -ldl -lm -o tfview
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_NO_STDIO
#define STBI_NO_LINEAR
#define STBI_NO_HDR
#define STBI_NO_THREAD_LOCALS
#include "third_party/stb_image.h"
#include "../capture/tfcodec.h"

#define IN_FIFO   "/tmp/tfview.in"
#define OUT_FIFO  "/tmp/tfview.out"
#define READY     "/tmp/tfview.ready"
#define MAXFRAME  (1u << 20)
#define BIT_SELECT 0
#define BIT_START  3

typedef int  (*fn_init_t)(void);
typedef void (*fn_deinit_t)(void);
typedef int  (*fn_disp_t)(void *src, int w, int h, int pitch);
static fn_init_t p_init; static fn_deinit_t p_deinit; static fn_disp_t p_disp;
static volatile sig_atomic_t g_quit;
static volatile uint32_t *g_keys;

static uint32_t now_ms(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint32_t)t.tv_sec * 1000u + (uint32_t)(t.tv_nsec / 1000000);
}
static void logf_(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void logf_(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    fprintf(stderr, "tfview: "); vfprintf(stderr, fmt, ap); fputc('\n', stderr);
    va_end(ap);
}

static int display_open(void) {
    const char *drv = getenv("TFVIEW_DRIVER");
    if (!drv) drv = "/mnt/sdcard/cubegm/driver_gb350.so";
    void *h = dlopen(drv, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { logf_("dlopen %s: %s", drv, dlerror()); return -1; }
    p_init = (fn_init_t)dlsym(h, "video_drivers_init");
    p_deinit = (fn_deinit_t)dlsym(h, "video_driver_deinit");
    p_disp = (fn_disp_t)dlsym(h, "video_driver_disp_frame");
    if (!p_init || !p_disp) { logf_("driver symbols missing"); return -1; }
    int rv = p_init();
    logf_("display driver %s init rv=%d", drv, rv);
    return rv > 0 ? 0 : -1;
}

/* black screen until the first frame; afterwards the last frame stays up */
static uint16_t g_black[320 * 240];
static void show_black(void) { p_disp(g_black, 320, 240, 640); }

static int keys_attach(void) {
    key_t k = ftok("/tmp/joy_key", 'a');
    int id = k == (key_t)-1 ? -1 : shmget(k, 4, 0666);
    if (id < 0) return -1;
    void *p = shmat(id, NULL, SHM_RDONLY);
    if (p == (void *)-1) return -1;
    g_keys = p;
    return 0;
}

static void on_sig(int s) { (void)s; g_quit = 1; }

int main(void) {
    signal(SIGTERM, on_sig); signal(SIGINT, on_sig); signal(SIGPIPE, SIG_IGN);
    unlink(READY);
    if (display_open() != 0) return 1;
    if (keys_attach() != 0) logf_("joy_key shared memory not found: buttons will not be sent");
    unlink(IN_FIFO); unlink(OUT_FIFO);
    if (mkfifo(IN_FIFO, 0666) != 0 || mkfifo(OUT_FIFO, 0666) != 0) { logf_("mkfifo: %s", strerror(errno)); return 1; }
    /* O_RDWR keeps both FIFOs open even while the PC side is not connected:
       reads never see EOF, writes never block or raise SIGPIPE */
    int in = open(IN_FIFO, O_RDWR | O_NONBLOCK), out = open(OUT_FIFO, O_RDWR | O_NONBLOCK);
    if (in < 0 || out < 0) { logf_("open fifo: %s", strerror(errno)); return 1; }
    close(open(READY, O_CREAT | O_WRONLY, 0644));
    logf_("ready: %s / %s", IN_FIFO, OUT_FIFO);

    uint8_t *buf = malloc(MAXFRAME + 64);
    uint16_t *rgb565 = malloc(640 * 480 * 2);
    if (!buf || !rgb565) return 1;
    size_t have = 0;
    uint32_t last_keys = 0xFFFFFFFFu, last_key_sent = 0, combo_since = 0, shown = 0, last_shown = 0;
    uint32_t frames = 0, decoded = 0, skipped = 0, t_stats = now_ms();
    int cw = 0, ch = 0, have_key = 0, dirty = 0;      /* tfcodec frame state */
    show_black();

    while (!g_quit) {
        struct pollfd pf = { in, POLLIN, 0 };
        poll(&pf, 1, 4);
        uint32_t t = now_ms();

        uint32_t keys = g_keys ? *g_keys : 0;
        uint32_t combo = (1u << BIT_SELECT) | (1u << BIT_START);
        if ((keys & combo) == combo) { if (!combo_since) combo_since = t; else if (t - combo_since > 1500) break; }
        else combo_since = 0;

        /* ---- frames from PC ---- */
        for (;;) {
            ssize_t r = read(in, buf + have, MAXFRAME + 64 - have);
            if (r > 0) { have += (size_t)r; if (have < MAXFRAME + 64) continue; }
            break;
        }
        /* walk complete packets, keep only the newest JPEG */
        size_t off = 0, best = 0, best_len = 0; int bw = 0, bh = 0, quit = 0;
        while (have - off >= 16) {
            uint32_t magic, len; uint16_t w, h;
            memcpy(&magic, buf + off, 4); memcpy(&len, buf + off + 4, 4);
            memcpy(&w, buf + off + 8, 2); memcpy(&h, buf + off + 10, 2);
            if (magic != 0x31564654u /* "TFV1" */ || len > MAXFRAME) {   /* resync */
                off++; continue;
            }
            if (len == 0) { quit = 1; off += 16; break; }
            if (have - off - 16 < len) break;
            uint8_t fmt = buf[off + 12];
            frames++;
            if (fmt == 2 || fmt == 3) {                   /* tfcodec: every packet, in order */
                if (w == 0 || h == 0 || w > 640 || h > 480 || (fmt == 3 && (!have_key || w != cw || h != ch))) {
                    skipped++;
                } else if (tfc_decode(buf + off + 16, len, fmt == 3 ? rgb565 : NULL, rgb565, w, h) == 0) {
                    cw = w; ch = h; have_key = 1; dirty = 1; decoded++;
                } else { logf_("bad tfcodec frame (%u bytes)", (unsigned)len); have_key = 0; }
                best_len = 0;                           /* a later JPEG would win, an earlier one is stale */
            } else {
                if (best_len) skipped++;
                best = off + 16; best_len = len; bw = w; bh = h;
            }
            off += 16 + len;
        }
        if (quit) break;
        if (best_len) {
            int w, h, n;
            uint8_t *px = stbi_load_from_memory(buf + best, (int)best_len, &w, &h, &n, 3);
            if (px && w > 0 && h > 0 && w <= 640 && h <= 480) {
                /* Always hand the driver the same frame size: a size change makes
                   it reprogram the scaler, which flashes the panel black. Small
                   (JPEG 320x240) frames are pixel-doubled to 640x480 here. */
                int sx = (w * 2 <= 640 && h * 2 <= 480) ? 2 : 1;
                int ow = w * sx, oh = h * sx;
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++) {
                        const uint8_t *q = px + 3 * (y * w + x);
                        uint16_t c = (uint16_t)(((q[0] & 0xF8) << 8) | ((q[1] & 0xFC) << 3) | (q[2] >> 3));
                        uint16_t *d = rgb565 + (size_t)(y * sx) * ow + x * sx;
                        d[0] = c;
                        if (sx == 2) { d[1] = c; d[ow] = c; d[ow + 1] = c; }
                    }
                p_disp(rgb565, ow, oh, ow * 2);
                decoded++; shown++; have_key = 0; dirty = 0;      /* JPEG overwrote the delta reference */
            } else if (!px) {
                logf_("bad JPEG (%u bytes, %dx%d announced): %s", (unsigned)best_len, bw, bh, stbi_failure_reason());
            }
            stbi_image_free(px);
        }
        if (off) { memmove(buf, buf + off, have - off); have -= off; }

        if (dirty) { p_disp(rgb565, cw, ch, cw * 2); dirty = 0; shown++; }

        /* ---- buttons + display ack -> PC ---- */
        keys = g_keys ? *g_keys : 0;
        t = now_ms();
        if (keys != last_keys || shown != last_shown || t - last_key_sent >= 100) {
            uint32_t rec[4] = { 0x324B4654u /* "TFK2" */, keys, shown, t };
            if (write(out, rec, sizeof rec) < 0 && errno != EAGAIN) logf_("status write: %s", strerror(errno));
            last_keys = keys; last_shown = shown; last_key_sent = t;
        }
        if (t - t_stats >= 5000) {
            logf_("frames %u decoded %u skipped %u keys 0x%08x", frames, decoded, skipped, keys);
            t_stats = t;
        }
    }
    logf_("exit (frames %u decoded %u)", frames, decoded);
    unlink(READY); unlink(IN_FIFO); unlink(OUT_FIFO);
    if (p_deinit) p_deinit();
    return 0;
}
