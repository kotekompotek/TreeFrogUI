/* SPDX-License-Identifier: MIT
 * Native Linux test of the actual backend with a synthetic DRM ioctl device.
 * No display device is opened and no target hardware is contacted.
 */
#define _GNU_SOURCE
#define _FILE_OFFSET_BITS 64
#include <assert.h>
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
static int fail_open, fail_modeset, closes, maps, sets, waits;
static unsigned char mock_pixels[1280 * 480];
static int fake_open(const char *path, int flags) { (void)path; (void)flags; if (fail_open) { errno=ENOENT; return -1; } return 42; }
static int fake_close(int fd) { assert(fd==42); closes++; return 0; }
static void *fake_mmap(void *p,size_t n,int prot,int flags,int fd,off_t offset) {
    (void)p;(void)prot;(void)flags; assert(fd==42 && n==sizeof(mock_pixels));
    assert(offset == (off_t)UINT64_C(0x100000000)); maps++; return mock_pixels;
}
static int fake_munmap(void *p,size_t n) { assert(p==mock_pixels && n==sizeof(mock_pixels)); return 0; }
static int fake_ioctl(int fd,unsigned long request,void *arg) {
    assert(fd==42);
    switch (request) {
    case DRM_IOCTL_VERSION: { struct drm_version *v=arg; strcpy(v->name,"r36-hc16xx"); break; }
    case DRM_IOCTL_MODE_GETRESOURCES: { struct drm_mode_card_res *r=arg; *(uint32_t *)(uintptr_t)r->crtc_id_ptr=10; *(uint32_t *)(uintptr_t)r->connector_id_ptr=11; r->count_crtcs=r->count_connectors=1; break; }
    case DRM_IOCTL_MODE_GETCONNECTOR: {
        struct drm_mode_get_connector *c=arg;
        struct drm_mode_modeinfo *m=(void *)(uintptr_t)c->modes_ptr;
        if (c->count_modes) {
            assert(c->props_ptr && c->prop_values_ptr && c->encoders_ptr && m);
            memset(m,0,sizeof(*m)); m->hdisplay=640;m->vdisplay=480;m->htotal=868;m->vtotal=518;
        }
        c->count_modes=c->count_encoders=c->count_props=c->connection=1; break;
    }
    case DRM_IOCTL_MODE_GETCRTC: { struct drm_mode_crtc *c=arg; c->mode_valid=0;c->fb_id=0;break; }
    case DRM_IOCTL_MODE_CREATE_DUMB: { struct drm_mode_create_dumb *d=arg; d->handle=12;d->pitch=1280;d->size=sizeof(mock_pixels); break; }
    case DRM_IOCTL_MODE_MAP_DUMB: { struct drm_mode_map_dumb *m=arg; m->offset=UINT64_C(0x100000000);break; }
    case DRM_IOCTL_MODE_ADDFB: { struct drm_mode_fb_cmd *f=arg; f->fb_id=13;break; }
    case DRM_IOCTL_MODE_SETCRTC: {
        struct drm_mode_crtc *c=arg;
        if (c->mode_valid) { if (fail_modeset) { errno=EIO;return -1; } sets++; }
        break;
    }
    case DRM_IOCTL_WAIT_VBLANK: waits++;break;
    case DRM_IOCTL_MODE_RMFB: case DRM_IOCTL_MODE_DESTROY_DUMB: break;
    default: assert(!"unexpected ioctl");
    }
    return 0;
}
#define open fake_open
#define close fake_close
#define mmap fake_mmap
#define munmap fake_munmap
#define ioctl fake_ioctl
#include "video_drm_backend.c"
#undef open
#undef close
#undef mmap
#undef munmap
#undef ioctl
unsigned int r36_test_backend_frames(void) { return (unsigned int)waits; }
unsigned int r36_test_backend_hash(void) {
    uint32_t hash=2166136261u;
    for (size_t i=0;i<sizeof(mock_pixels);i++) hash=(hash^mock_pixels[i])*16777619u;
    return hash;
}
#ifndef R36_BACKEND_TEST_LIBRARY
int main(void) {
    uint16_t frame[320*240];
    for (unsigned i=0;i<320*240;i++) frame[i]=0x1234;
    fail_open=1;assert(video_drivers_init()==-1);assert(device==-1);
    fail_open=0;assert(video_drivers_init()>0);assert(video_drivers_init()>0);assert(maps==1);
    assert(video_driver_disp_frame(NULL,320,240,640)==-1 && sets==0);
    fail_modeset=1;assert(video_driver_disp_frame(frame,320,240,640)==-1 && sets==0);
    fail_modeset=0;assert(video_driver_disp_frame(frame,320,240,640)==0);
    assert(sets==1 && waits==1);
    assert(mock_pixels[0]==0x34 && mock_pixels[1]==0x12);
    assert(video_driver_disp_frame(frame,320,240,640)==0 && sets==1 && waits==2);
    video_driver_deinit();assert(device==-1 && closes==1);
    video_driver_deinit();assert(closes==1);
    assert(video_driver_disp_frame(frame,320,240,640)==-1);
    puts("REAL_BACKEND_MOCK_DRM=PASS (not hardware acceptance)");
    return 0;
}
#endif
