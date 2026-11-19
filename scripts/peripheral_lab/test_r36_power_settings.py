"""Verify r36_power_settings.c UI state, R36S physical keycodes, RGB565 rendering, and MIPS32r2 DRM build."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ZIG = Path(r"C:\Users\palpa\Tools\zig-x86_64-windows-0.17.0\zig.exe")


def test_r36_power_settings_ui_keys_and_mips_drm_build(tmp_path):
    src = ROOT / "scripts/peripheral_lab/r36_power_settings.c"
    conf = tmp_path / "r36_sysd.conf"
    harness = tmp_path / "power_ui_test.c"
    harness.write_text(
        f'''
#include <assert.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void *mock_mmap(void *a, size_t l, int p, int f, int fd, long o) {{
    (void)a; (void)l; (void)p; (void)f; (void)fd; (void)o; return (void *)(-1);
}}
static int mock_munmap(void *a, size_t l) {{ (void)a; (void)l; return 0; }}
#define mmap   mock_mmap
#define munmap mock_munmap

#define R36_POWER_SETTINGS_MOCK 1
#include "{src.as_posix()}"

static uint16_t fake_fb[R36_FB_WIDTH * R36_FB_HEIGHT];

int main(void) {{
    struct r36_power_ui_state ui;
    r36_power_ui_init(&ui, "{conf.as_posix()}");
    assert(ui.cursor == R36_ROW_SCREEN_OFF);

    /* Test R36S physical serial keycodes: DOWN(713), RIGHT(714), LEFT(715), UP(712), A(705), B(704) */
    assert(r36_power_ui_step_key(&ui, 713, 1) == R36_UI_CONTINUE);
    assert(ui.cursor == R36_ROW_AUTO_POWEROFF);
    assert(r36_power_ui_step_key(&ui, 713, 1) == R36_UI_CONTINUE);
    assert(ui.cursor == R36_ROW_VOLUME);
    int v0 = ui.conf.volume_pct;
    assert(r36_power_ui_step_key(&ui, 714, 1) == R36_UI_CONTINUE);
    assert(ui.conf.volume_pct == r36_conf_clamp_int(v0 + 5, 0, 100));
    assert(r36_power_ui_step_key(&ui, 715, 1) == R36_UI_CONTINUE);
    assert(ui.conf.volume_pct == v0);

    /* Render RGB565 UI and verify non-uniform pixels */
    memset(fake_fb, 0, sizeof(fake_fb));
    r36_power_ui_render(fake_fb, &ui);
    int nonzero = 0;
    for (int i = 0; i < R36_FB_WIDTH * R36_FB_HEIGHT; i++) {{
        if (fake_fb[i] != 0) nonzero++;
    }}
    assert(nonzero > 10000);

    /* Save via R36S A button (705) and verify config persisted */
    assert(r36_power_ui_step_key(&ui, 712, 1) == R36_UI_CONTINUE);
    assert(r36_power_ui_step_key(&ui, 714, 1) == R36_UI_CONTINUE);
    assert(r36_power_ui_step_key(&ui, 705, 1) == R36_UI_SAVED_EXIT);
    assert(ui.dirty == 0);

    /* Cancel via R36S B button (704) */
    assert(r36_power_ui_step_key(&ui, 704, 1) == R36_UI_CANCEL_EXIT);
    puts("R36_POWER_SETTINGS=PASS");
    return 0;
}}
''',
        encoding="utf-8",
    )
    exe = tmp_path / "power_ui_test.exe"
    subprocess.run(
        ["gcc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", str(harness), "-o", str(exe)],
        check=True,
        capture_output=True,
        timeout=20,
    )
    res = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=5)
    assert "R36_POWER_SETTINGS=PASS" in res.stdout
    assert conf.is_file()

    if ZIG.exists():
        mips_elf = tmp_path / "r36-power-settings.elf"
        subprocess.run(
            [
                str(ZIG),
                "cc",
                "-target",
                "mipsel-linux.4.4-musleabi",
                "-march=mips32r2",
                "-msoft-float",
                "-Os",
                "-static",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(src),
                "-o",
                str(mips_elf),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        assert mips_elf.stat().st_size > 0
