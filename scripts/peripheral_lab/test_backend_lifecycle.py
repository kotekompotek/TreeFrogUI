from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_dummy_sound_or_ge_exports_and_retains_failed_dma_cleanup():
    text = (ROOT / "scripts/peripheral_lab/video_drm_backend.c").read_text()
    assert "int video_drivers_init(void)" in text
    assert "int video_driver_disp_frame(void *source, int width, int height, int pitch_bytes)" in text
    assert "void video_driver_deinit(void)" in text
    assert "sound_driver_init(" not in text and "sound_driver_playframe(" not in text
    assert "void *g_render" not in text
    assert "restore failed; retaining scanout buffer until reset" in text
    assert "disable failed; retaining scanout buffer until reset" in text
    assert "#define _FILE_OFFSET_BITS 64" in text


def test_publisher_does_not_steal_existing_shm_or_report_disconnect_as_success():
    text = (ROOT / "scripts/peripheral_lab/legacy_keys.c").read_text()
    assert "IPC_CREAT | IPC_EXCL | 0600" in text
    assert "LOCK_EX | LOCK_NB" in text
    assert "result = requested_stop ? 0 : 1;" in text
    assert "SYN_DROPPED" in text
    assert "*shared = stopped ? 0 : r36_key_word(&state);" in text
