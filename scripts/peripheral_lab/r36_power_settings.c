/* SPDX-License-Identifier: MIT
 * On-console framebuffer + evdev settings editor & CLI for R36S power/display timers:
 *  - Screen Off Timer (OFF / 30S / 1M / 2M / 5M / 10M / 15M; 5s smooth fade before off)
 *  - Auto Poweroff Timer (OFF / 5M / 10M / 15M / 30M / 60M)
 *  - Volume % (0..100) and Brightness % (5..100)
 * Persists to /mnt/sdcard/cubegm/r36_sysd.conf (hot-reloaded by r36_sysd).
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#ifndef _FILE_OFFSET_BITS
#define _FILE_OFFSET_BITS 64
#endif

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef R36_POWER_SETTINGS_MOCK
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#else
#define R36_SCREEN_STATUS_MOCK 1
#endif

#include "../kernel_lab/r36_screen_status.h"
#include "r36_sysd_conf.h"

#ifndef EV_KEY
#define EV_KEY 0x01
#endif

/* Standard Linux evdev keycodes used on R36S (D-pad + A/B/START/SELECT) */
#ifndef KEY_UP
#define KEY_UP     103
#endif
#ifndef KEY_DOWN
#define KEY_DOWN   108
#endif
#ifndef KEY_LEFT
#define KEY_LEFT   105
#endif
#ifndef KEY_RIGHT
#define KEY_RIGHT  106
#endif
#ifndef KEY_ENTER
#define KEY_ENTER  28
#endif
#ifndef KEY_ESC
#define KEY_ESC    1
#endif
#ifndef BTN_SOUTH
#define BTN_SOUTH  304
#endif
#ifndef BTN_EAST
#define BTN_EAST   305
#endif
#ifndef BTN_SELECT
#define BTN_SELECT 314
#endif
#ifndef BTN_START
#define BTN_START  315
#endif

enum r36_power_ui_row {
    R36_ROW_SCREEN_OFF = 0,
    R36_ROW_AUTO_POWEROFF = 1,
    R36_ROW_VOLUME = 2,
    R36_ROW_BRIGHTNESS = 3,
    R36_ROW_SAVE_EXIT = 4,
    R36_ROW_COUNT = 5
};

enum r36_power_ui_result {
    R36_UI_CONTINUE = 0,
    R36_UI_SAVED_EXIT = 1,
    R36_UI_CANCEL_EXIT = 2
};

struct r36_power_ui_state {
    struct r36_sysd_conf conf;
    int cursor;
    int dirty;
    const char *conf_path;
};

static const int k_screen_off_presets[] = { 0, 30, 60, 120, 300, 600, 900 };
static const int k_auto_poweroff_presets[] = { 0, 300, 600, 900, 1800, 3600 };

static int r36_step_preset(int current, const int *presets, int count, int dir)
{
    int i;
    if (dir > 0) {
        for (i = 0; i < count; i++) {
            if (presets[i] > current)
                return presets[i];
        }
        return presets[0];
    }
    for (i = count - 1; i >= 0; i--) {
        if (presets[i] < current)
            return presets[i];
    }
    return presets[count - 1];
}

static void r36_format_duration(int sec, char *out, size_t out_sz)
{
    if (sec <= 0)
        snprintf(out, out_sz, "OFF");
    else if (sec < 60 || (sec % 60) != 0)
        snprintf(out, out_sz, "%dS", sec);
    else
        snprintf(out, out_sz, "%dM", sec / 60);
}

static void r36_power_ui_init(struct r36_power_ui_state *ui, const char *conf_path)
{
    memset(ui, 0, sizeof(*ui));
    ui->conf_path = conf_path ? conf_path : R36_SYSD_CONF_DEFAULT_PATH;
    r36_sysd_conf_defaults(&ui->conf);
    (void)r36_sysd_conf_load(ui->conf_path, &ui->conf);
}

static enum r36_power_ui_result r36_power_ui_step_key(struct r36_power_ui_state *ui,
                                                      uint16_t code, int32_t value)
{
    int dir = 0;
    if (value == 0)
        return R36_UI_CONTINUE;

    if (code == KEY_UP || code == 712) {
        ui->cursor = (ui->cursor + R36_ROW_COUNT - 1) % R36_ROW_COUNT;
        return R36_UI_CONTINUE;
    }
    if (code == KEY_DOWN || code == 713) {
        ui->cursor = (ui->cursor + 1) % R36_ROW_COUNT;
        return R36_UI_CONTINUE;
    }
    if (code == KEY_LEFT || code == 715)
        dir = -1;
    else if (code == KEY_RIGHT || code == 714)
        dir = 1;

    if (dir != 0) {
        switch (ui->cursor) {
        case R36_ROW_SCREEN_OFF:
            ui->conf.screen_off_sec = r36_step_preset(
                ui->conf.screen_off_sec, k_screen_off_presets,
                (int)(sizeof(k_screen_off_presets) / sizeof(k_screen_off_presets[0])), dir);
            ui->dirty = 1;
            break;
        case R36_ROW_AUTO_POWEROFF:
            ui->conf.auto_poweroff_sec = r36_step_preset(
                ui->conf.auto_poweroff_sec, k_auto_poweroff_presets,
                (int)(sizeof(k_auto_poweroff_presets) / sizeof(k_auto_poweroff_presets[0])), dir);
            ui->dirty = 1;
            break;
        case R36_ROW_VOLUME:
            ui->conf.volume_pct = r36_conf_clamp_int(ui->conf.volume_pct + dir * 5, 0, 100);
            ui->dirty = 1;
            break;
        case R36_ROW_BRIGHTNESS:
            ui->conf.brightness_pct = r36_conf_clamp_int(ui->conf.brightness_pct + dir * 5, 5, 100);
            ui->dirty = 1;
            break;
        default:
            break;
        }
        return R36_UI_CONTINUE;
    }

    if (code == BTN_SOUTH || code == BTN_START || code == KEY_ENTER || code == 705 || code == 711) {
        (void)r36_sysd_conf_save(ui->conf_path, &ui->conf);
        ui->dirty = 0;
        return R36_UI_SAVED_EXIT;
    }
    if (code == BTN_EAST || code == BTN_SELECT || code == KEY_ESC || code == 704 || code == 710)
        return R36_UI_CANCEL_EXIT;

    return R36_UI_CONTINUE;
}

static void r36_power_ui_render(uint16_t *fb, const struct r36_power_ui_state *ui)
{
    static const char *const labels[R36_ROW_COUNT] = {
        "SCREEN OFF TIMER",
        "AUTO POWEROFF",
        "VOLUME",
        "BRIGHTNESS",
        "SAVE AND EXIT"
    };
    char val_buf[32];
    int i;

    if (!fb || !ui)
        return;

    r36_fb_fill_rect(fb, 0, 0, R36_FB_WIDTH, R36_FB_HEIGHT, 0x0842u);
    r36_fb_fill_rect(fb, 28, 36, R36_FB_WIDTH - 56, 4, 0xBDF7u);
    r36_fb_fill_rect(fb, 28, R36_FB_HEIGHT - 44, R36_FB_WIDTH - 56, 4, 0xBDF7u);
    r36_fb_draw_text(fb, 40, 56, "R36S POWER SETTINGS", 0xFFFFu, 3);

    for (i = 0; i < R36_ROW_COUNT; i++) {
        int y = 128 + i * 52;
        uint16_t row_bg = (i == ui->cursor) ? 0x1A50u : 0x1084u;
        uint16_t fg = (i == ui->cursor) ? 0xFFE0u : 0xFFFFu;

        r36_fb_fill_rect(fb, 40, y - 8, R36_FB_WIDTH - 80, 40, row_bg);
        r36_fb_draw_text(fb, 56, y + 4, labels[i], fg, 2);

        val_buf[0] = '\0';
        if (i == R36_ROW_SCREEN_OFF)
            r36_format_duration(ui->conf.screen_off_sec, val_buf, sizeof(val_buf));
        else if (i == R36_ROW_AUTO_POWEROFF)
            r36_format_duration(ui->conf.auto_poweroff_sec, val_buf, sizeof(val_buf));
        else if (i == R36_ROW_VOLUME)
            snprintf(val_buf, sizeof(val_buf), "%d%%", ui->conf.volume_pct);
        else if (i == R36_ROW_BRIGHTNESS)
            snprintf(val_buf, sizeof(val_buf), "%d%%", ui->conf.brightness_pct);

        if (val_buf[0] != '\0')
            r36_fb_draw_text(fb, 440, y + 4, val_buf, fg, 2);
    }

    r36_fb_draw_text(fb, 40, 404, "A/START: SAVE   B/SELECT: CANCEL", 0xDEFBu, 2);
}

#ifndef R36_POWER_SETTINGS_MOCK
static int r36_open_evdev_opt(const char *path)
{
    return path ? open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC) : -1;
}

static int r36_run_cli(int argc, char **argv, const char *conf_path)
{
    struct r36_sysd_conf c;
    int i, get_only = 0, modified = 0;

    r36_sysd_conf_defaults(&c);
    (void)r36_sysd_conf_load(conf_path, &c);

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--config") && i + 1 < argc) {
            i++;
        } else if (!strcmp(argv[i], "--get")) {
            get_only = 1;
        } else if (!strcmp(argv[i], "--screen-off") && i + 1 < argc) {
            c.screen_off_sec = atoi(argv[++i]);
            modified = 1;
        } else if (!strcmp(argv[i], "--auto-poweroff") && i + 1 < argc) {
            c.auto_poweroff_sec = atoi(argv[++i]);
            modified = 1;
        } else if (!strcmp(argv[i], "--volume") && i + 1 < argc) {
            c.volume_pct = atoi(argv[++i]);
            modified = 1;
        } else if (!strcmp(argv[i], "--brightness") && i + 1 < argc) {
            c.brightness_pct = atoi(argv[++i]);
            modified = 1;
        } else {
            fprintf(stderr, "Usage: %s [--config PATH] [--get] [--screen-off SEC] [--auto-poweroff SEC] [--volume PCT] [--brightness PCT]\n", argv[0]);
            return 2;
        }
    }

    r36_sysd_conf_clamp(&c);
    if (modified) {
        if (r36_sysd_conf_save(conf_path, &c) != 0) {
            perror("save config");
            return 1;
        }
    }
    if (get_only || modified) {
        printf("volume_pct=%d\nbrightness_pct=%d\nscreen_off_sec=%d\nauto_poweroff_sec=%d\n",
               c.volume_pct, c.brightness_pct, c.screen_off_sec, c.auto_poweroff_sec);
        return 0;
    }
    return -1;
}

struct r36_surface {
    int fd;
    int is_drm;
    uint16_t *fb;
    size_t fb_bytes;
    uint32_t conn_id;
    uint32_t crtc_id;
    uint32_t fb_id;
    uint32_t handle;
    struct drm_mode_crtc prev_crtc;
};

static void r36_surface_close(struct r36_surface *s)
{
    if (!s || s->fd < 0)
        return;
    if (s->is_drm) {
        if (s->prev_crtc.mode_valid && s->prev_crtc.fb_id) {
            s->prev_crtc.set_connectors_ptr = (uintptr_t)&s->conn_id;
            s->prev_crtc.count_connectors = 1;
            (void)ioctl(s->fd, DRM_IOCTL_MODE_SETCRTC, &s->prev_crtc);
        }
        if (s->fb && s->fb != MAP_FAILED)
            munmap(s->fb, s->fb_bytes);
        if (s->fb_id)
            (void)ioctl(s->fd, DRM_IOCTL_MODE_RMFB, &s->fb_id);
        if (s->handle) {
            struct drm_mode_destroy_dumb dd = { .handle = s->handle };
            (void)ioctl(s->fd, DRM_IOCTL_MODE_DESTROY_DUMB, &dd);
        }
    } else {
        if (s->fb && s->fb != MAP_FAILED)
            munmap(s->fb, s->fb_bytes);
    }
    close(s->fd);
    s->fd = -1;
    s->fb = NULL;
}

static int r36_surface_open_drm(struct r36_surface *s)
{
    uint32_t conns[8], crtcs[8];
    struct drm_mode_card_res res;
    struct drm_mode_get_connector conn;
    struct drm_mode_modeinfo modes[8], chosen;
    struct drm_mode_create_dumb dumb;
    struct drm_mode_map_dumb map;
    struct drm_mode_fb_cmd fb_cmd;
    struct drm_mode_crtc set;
    int fd, found = 0;

    fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
    if (fd < 0)
        return -1;
    memset(s, 0, sizeof(*s));
    s->fd = fd;
    s->is_drm = 1;
    s->fb = MAP_FAILED;

    memset(&res, 0, sizeof(res));
    res.connector_id_ptr = (uintptr_t)conns;
    res.crtc_id_ptr = (uintptr_t)crtcs;
    res.count_connectors = 8;
    res.count_crtcs = 8;
    if (ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res) != 0 || res.count_connectors == 0 || res.count_crtcs == 0)
        goto fail;

    s->conn_id = conns[0];
    s->crtc_id = crtcs[0];
    memset(&conn, 0, sizeof(conn));
    conn.connector_id = s->conn_id;
    conn.modes_ptr = (uintptr_t)modes;
    conn.count_modes = 8;
    if (ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &conn) != 0 || conn.count_modes == 0)
        goto fail;

    chosen = modes[0];
    for (uint32_t i = 0; i < conn.count_modes && i < 8; i++) {
        if (modes[i].hdisplay == R36_FB_WIDTH && modes[i].vdisplay == R36_FB_HEIGHT) {
            chosen = modes[i];
            found = 1;
            break;
        }
    }
    (void)found;

    memset(&s->prev_crtc, 0, sizeof(s->prev_crtc));
    s->prev_crtc.crtc_id = s->crtc_id;
    (void)ioctl(fd, DRM_IOCTL_MODE_GETCRTC, &s->prev_crtc);

    memset(&dumb, 0, sizeof(dumb));
    dumb.width = R36_FB_WIDTH;
    dumb.height = R36_FB_HEIGHT;
    dumb.bpp = 16;
    if (ioctl(fd, DRM_IOCTL_MODE_CREATE_DUMB, &dumb) != 0)
        goto fail;
    s->handle = dumb.handle;
    s->fb_bytes = (size_t)dumb.size;

    memset(&map, 0, sizeof(map));
    map.handle = s->handle;
    if (ioctl(fd, DRM_IOCTL_MODE_MAP_DUMB, &map) != 0)
        goto fail;
    s->fb = (uint16_t *)mmap(NULL, s->fb_bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, (off_t)map.offset);
    if (s->fb == MAP_FAILED)
        goto fail;

    memset(&fb_cmd, 0, sizeof(fb_cmd));
    fb_cmd.width = R36_FB_WIDTH;
    fb_cmd.height = R36_FB_HEIGHT;
    fb_cmd.pitch = dumb.pitch;
    fb_cmd.bpp = 16;
    fb_cmd.depth = 16;
    fb_cmd.handle = s->handle;
    if (ioctl(fd, DRM_IOCTL_MODE_ADDFB, &fb_cmd) != 0)
        goto fail;
    s->fb_id = fb_cmd.fb_id;

    memset(&set, 0, sizeof(set));
    set.set_connectors_ptr = (uintptr_t)&s->conn_id;
    set.count_connectors = 1;
    set.crtc_id = s->crtc_id;
    set.fb_id = s->fb_id;
    set.mode = chosen;
    set.mode_valid = 1;
    if (ioctl(fd, DRM_IOCTL_MODE_SETCRTC, &set) != 0)
        goto fail;
    return 0;

fail:
    r36_surface_close(s);
    return -1;
}

static int r36_surface_open(struct r36_surface *s)
{
    if (r36_surface_open_drm(s) == 0)
        return 0;
    memset(s, 0, sizeof(*s));
    s->fb_bytes = (size_t)R36_FB_WIDTH * (size_t)R36_FB_HEIGHT * sizeof(uint16_t);
    s->fd = open("/dev/fb0", O_RDWR | O_CLOEXEC);
    if (s->fd < 0)
        return -1;
    s->fb = (uint16_t *)mmap(NULL, s->fb_bytes, PROT_READ | PROT_WRITE, MAP_SHARED, s->fd, 0);
    if (s->fb == MAP_FAILED) {
        close(s->fd);
        s->fd = -1;
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *conf_path = R36_SYSD_CONF_DEFAULT_PATH;
    int i, cli_rc;
    int fd0, fd1;
    struct r36_surface surf;
    struct r36_power_ui_state ui;
    enum r36_power_ui_result res = R36_UI_CONTINUE;

    for (i = 1; i + 1 < argc; i++) {
        if (!strcmp(argv[i], "--config"))
            conf_path = argv[i + 1];
    }
    if (argc > 1) {
        cli_rc = r36_run_cli(argc, argv, conf_path);
        if (cli_rc >= 0)
            return cli_rc;
    }

    if (r36_surface_open(&surf) != 0)
        return 1;

    fd0 = r36_open_evdev_opt("/dev/input/event0");
    fd1 = r36_open_evdev_opt("/dev/input/event1");
    r36_power_ui_init(&ui, conf_path);
    r36_power_ui_render(surf.fb, &ui);

    while (res == R36_UI_CONTINUE) {
        struct pollfd pfds[2];
        nfds_t nfds = 0;
        int fds[2];
        int k;

        if (fd0 >= 0) {
            fds[nfds] = fd0;
            pfds[nfds].fd = fd0;
            pfds[nfds].events = POLLIN;
            pfds[nfds].revents = 0;
            nfds++;
        }
        if (fd1 >= 0) {
            fds[nfds] = fd1;
            pfds[nfds].fd = fd1;
            pfds[nfds].events = POLLIN;
            pfds[nfds].revents = 0;
            nfds++;
        }
        if (nfds == 0)
            break;
        (void)poll(pfds, nfds, 250);
        for (k = 0; k < (int)nfds && res == R36_UI_CONTINUE; k++) {
            struct input_event ev;
            while (read(fds[k], &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
                if (ev.type == EV_KEY) {
                    res = r36_power_ui_step_key(&ui, ev.code, ev.value);
                    r36_power_ui_render(surf.fb, &ui);
                    if (res != R36_UI_CONTINUE)
                        break;
                }
            }
        }
    }

    if (fd0 >= 0) close(fd0);
    if (fd1 >= 0) close(fd1);
    r36_surface_close(&surf);
    return 0;
}
#endif
