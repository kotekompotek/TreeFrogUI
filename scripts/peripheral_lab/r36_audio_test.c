/* SPDX-License-Identifier: MIT */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "audio_alsa_backend.c"

int main(int argc, char **argv)
{
    int freq_hz = (argc > 1) ? atoi(argv[1]) : 1000;
    int dur_ms = (argc > 2) ? atoi(argv[2]) : 2000;
    int amp = (argc > 3) ? atoi(argv[3]) : 12000;
    int total_frames, pos = 0;
    int16_t buf[R36_AUDIO_PERIOD_FRAMES * 2];

    if (freq_hz < 50 || freq_hz > 12000)
        freq_hz = 1000;
    if (dur_ms < 100 || dur_ms > 10000)
        dur_ms = 2000;
    if (amp < 100 || amp > 30000)
        amp = 12000;

    if (sound_driver_init(NULL, R36_AUDIO_HW_RATE, R36_AUDIO_HW_CHANNELS) != 0) {
        fprintf(stderr, "r36-audio-test: sound_driver_init failed errno=%d\n", errno);
        return 1;
    }

    total_frames = (R36_AUDIO_HW_RATE * dur_ms) / 1000;
    while (pos < total_frames) {
        int chunk = total_frames - pos;
        if (chunk > (int)R36_AUDIO_PERIOD_FRAMES)
            chunk = R36_AUDIO_PERIOD_FRAMES;
        for (int i = 0; i < chunk; i++) {
            double phase = 2.0 * 3.14159265358979323846 * (double)freq_hz * (double)(pos + i) / (double)R36_AUDIO_HW_RATE;
            int16_t s = (int16_t)(sin(phase) * (double)amp);
            buf[i * 2 + 0] = s;
            buf[i * 2 + 1] = s;
        }
        if (sound_driver_playframe(buf, (unsigned int)chunk) < 0) {
            fprintf(stderr, "r36-audio-test: playframe failed at %d\n", pos);
            sound_driver_deinit();
            return 2;
        }
        pos += chunk;
    }

    usleep(200000);
    sound_driver_deinit();
    printf("r36-audio-test: played freq=%dHz dur=%dms frames=%d\n", freq_hz, dur_ms, total_frames);
    return 0;
}
