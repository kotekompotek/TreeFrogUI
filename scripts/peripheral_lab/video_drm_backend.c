/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#define _FILE_OFFSET_BITS 64
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include "rgb565_scale.h"

/* New backend, not a wrapper around the stock driver. Only observed video ABI
 * is exported; optional GE objects and unimplemented sound are deliberately
 * absent. Errors return -1. No dummy-success or MMIO access is used.
 */
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static int device = -1, active;
static unsigned long submitted_frames;
static uint32_t connector_id, crtc_id, framebuffer, handle, stride;
static uint64_t buffer_size;
static void *pixels = MAP_FAILED;
static struct drm_mode_modeinfo native_mode;
static struct drm_mode_crtc previous;

#ifdef R36_SCANOUT_TRACE
#include "video_scanout_trace.h"
#endif

static void cleanup(void)
{
    if (device < 0) return;
    if (active) {
        if (previous.mode_valid && previous.fb_id) {
            previous.set_connectors_ptr = (uintptr_t)&connector_id;
            previous.count_connectors = 1;
            if (ioctl(device, DRM_IOCTL_MODE_SETCRTC, &previous)) {
                fputs("r36-drm: restore failed; retaining scanout buffer until reset\n", stderr);
                return;
            }
        } else {
            struct drm_mode_crtc off = {.crtc_id = crtc_id};
            if (ioctl(device, DRM_IOCTL_MODE_SETCRTC, &off)) {
                fputs("r36-drm: disable failed; retaining scanout buffer until reset\n", stderr);
                return;
            }
        }
    }
    active = 0;
    if (pixels != MAP_FAILED) munmap(pixels, buffer_size);
    pixels = MAP_FAILED;
    if (framebuffer) ioctl(device, DRM_IOCTL_MODE_RMFB, &framebuffer);
    if (handle) {
        struct drm_mode_destroy_dumb destroy = {.handle = handle};
        ioctl(device, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy);
    }
    close(device); device = -1;
    framebuffer = handle = stride = 0; buffer_size = 0;
}

int video_drivers_init(void)
{
    struct drm_version version = {0};
    char name[64] = {0};
    struct drm_mode_card_res resources = {0};
    struct drm_mode_get_connector connector = {0};
    struct drm_mode_modeinfo modes[64];
    struct drm_mode_create_dumb dumb = {.width = 640, .height = 480, .bpp = 16};
    struct drm_mode_map_dumb map = {0};
    struct drm_mode_fb_cmd fb = {0};
    uint32_t crtcs[64], connectors[64], encoders[64], props[64];
    uint64_t values[64];
    const char *path = getenv("R36_DRM_DEVICE");
    int found = 0, result = -1;
    const char *phase = "open";
    unsigned int i;
    pthread_mutex_lock(&lock);
    if (device >= 0) { result = 1; goto finish; }
    device = open(path ? path : "/dev/dri/card0", O_RDWR | O_CLOEXEC);
    if (device < 0) goto fail;
    phase = "version";
    version.name = name; version.name_len = sizeof(name) - 1;
    if (ioctl(device, DRM_IOCTL_VERSION, &version) || strcmp(name, "r36-hc16xx")) goto fail;
    phase = "resources";
    resources.crtc_id_ptr = (uintptr_t)crtcs; resources.count_crtcs = 64;
    resources.connector_id_ptr = (uintptr_t)connectors; resources.count_connectors = 64;
    if (ioctl(device, DRM_IOCTL_MODE_GETRESOURCES, &resources) || resources.count_crtcs != 1 || resources.count_connectors != 1) goto fail;
    phase = "connector";
    connector_id = connectors[0]; crtc_id = crtcs[0];
    connector.connector_id = connector_id;
    /* A zero-mode count query asks DRM to populate/probe connector modes.
     * Passing a full buffer immediately can return an unprobed empty list. */
    if (ioctl(device, DRM_IOCTL_MODE_GETCONNECTOR, &connector)) goto fail;
    if (connector.count_modes > 64 || connector.count_encoders > 64 || connector.count_props > 64) {
        errno = EOVERFLOW; goto fail;
    }
    connector.modes_ptr = (uintptr_t)modes; connector.count_modes = 64;
    connector.encoders_ptr = (uintptr_t)encoders; connector.count_encoders = 64;
    connector.props_ptr = (uintptr_t)props; connector.prop_values_ptr = (uintptr_t)values; connector.count_props = 64;
    if (ioctl(device, DRM_IOCTL_MODE_GETCONNECTOR, &connector)) goto fail;
    if (connector.connection != 1 || connector.count_modes > 64 || connector.count_encoders > 64 || connector.count_props > 64) {
        errno = connector.connection != 1 ? ENODEV : EOVERFLOW; goto fail;
    }
    for (i = 0; i < connector.count_modes; i++) {
        if (modes[i].hdisplay == 640 && modes[i].vdisplay == 480 &&
            modes[i].htotal == 868 && modes[i].vtotal == 518) {
            native_mode = modes[i]; found = 1; break;
        }
    }
    if (!found) { errno = ENOENT; goto fail; }
    phase = "getcrtc";
    memset(&previous, 0, sizeof(previous)); previous.crtc_id = crtc_id;
    if (ioctl(device, DRM_IOCTL_MODE_GETCRTC, &previous)) goto fail;
    phase = "create_dumb";
    if (ioctl(device, DRM_IOCTL_MODE_CREATE_DUMB, &dumb)) goto fail;
    handle = dumb.handle; stride = dumb.pitch; buffer_size = dumb.size;
    if (stride < 1280 || stride > 65536 || buffer_size < (uint64_t)stride * 480 || buffer_size > 16 * 1024 * 1024) goto fail;
    phase = "map_dumb";
    map.handle = handle;
    if (ioctl(device, DRM_IOCTL_MODE_MAP_DUMB, &map)) goto fail;
    fprintf(stderr, "r36-drm: pitch=%u bytes=%llu offset=%llu off_t_bytes=%u\n", stride,
            (unsigned long long)buffer_size, (unsigned long long)map.offset, (unsigned int)sizeof(off_t));
    phase = "mmap";
    pixels = mmap(NULL, buffer_size, PROT_READ | PROT_WRITE, MAP_SHARED, device, (off_t)map.offset);
    if (pixels == MAP_FAILED) goto fail;
    memset(pixels, 0, buffer_size);
    fb.width = 640; fb.height = 480; fb.pitch = stride; fb.bpp = fb.depth = 16; fb.handle = handle;
    phase = "addfb";
    if (ioctl(device, DRM_IOCTL_MODE_ADDFB, &fb)) goto fail;
    framebuffer = fb.fb_id;
    result = 1;
    goto finish;
fail:
    fprintf(stderr, "r36-drm: init failed phase=%s errno=%d\n", phase, errno);
    cleanup();
finish:
    pthread_mutex_unlock(&lock);
    return result;
}

int video_driver_disp_frame(void *source, int width, int height, int pitch_bytes)
{
    int result = -1;
    pthread_mutex_lock(&lock);
    if (device < 0 || r36_scale565(pixels, stride, source, width, height, pitch_bytes)) goto finish;
    __sync_synchronize();
#ifdef R36_SCANOUT_TRACE
    if (!submitted_frames) {
        scanout_expected_hash = scanout_hash(pixels, stride);
        scanout_expected_ready = 1;
        if (source && width == 640 && height == 480 && pitch_bytes == 1280)
            fprintf(stderr, "r36-scanout: callback_source=%08x scaled_target=%08x identity_geometry=1\n",
                    scanout_hash(source, pitch_bytes), scanout_expected_hash);
    }
#endif
    if (!active) {
        struct drm_mode_crtc crtc = {.set_connectors_ptr = (uintptr_t)&connector_id,
            .count_connectors = 1, .crtc_id = crtc_id, .fb_id = framebuffer, .mode_valid = 1,
            .mode = native_mode};
        if (ioctl(device, DRM_IOCTL_MODE_SETCRTC, &crtc)) goto finish;
        active = 1;
    }
    {
        union drm_wait_vblank wait = {0};
        wait.request.type = _DRM_VBLANK_RELATIVE; wait.request.sequence = 1;
        if (ioctl(device, DRM_IOCTL_WAIT_VBLANK, &wait)) goto finish;
    }
    submitted_frames++;
#ifdef R36_SCANOUT_TRACE
    if (submitted_frames == 1) scanout_trace("first", scanout_expected_hash, scanout_expected_ready);
#endif
    if (submitted_frames == 1 || submitted_frames % 60 == 0)
        fprintf(stderr, "r36-drm: submitted_frames=%lu source=%dx%d pitch=%d\n", submitted_frames, width, height, pitch_bytes);
    result = 0;
finish:
    pthread_mutex_unlock(&lock);
    return result;
}

void video_driver_deinit(void)
{
    pthread_mutex_lock(&lock);
#ifdef R36_SCANOUT_TRACE
    if (submitted_frames == 1) scanout_trace("before_cleanup", scanout_expected_hash, scanout_expected_ready);
#endif
    cleanup();
    pthread_mutex_unlock(&lock);
}
