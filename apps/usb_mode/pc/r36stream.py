#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Pavel Kotek
"""r36stream - stream the PC screen to the R36S and use the console as a gamepad.

    python r36stream.py                      whole desktop, 640x480, lossless, Xbox 360 pad
    python r36stream.py --window "Title"     one window (exact title, as ffmpeg gdigrab sees it)
    python r36stream.py --crop 0,0,1280,960  a desktop region x,y,w,h (sharper than the whole desktop)
    python r36stream.py --codec raw          always lossless (desktop work)
    python r36stream.py --codec jpeg         always JPEG
    python r36stream.py --pad-mode sticks    start in a different gamepad mode
    python r36stream.py --no-pad             video only

Codec "auto" (default) sends lossless frames while the picture is mostly still
and switches to 320x240 JPEG while a lot of it moves, then back.

Gamepad modes (SELECT + R1 on the console cycles them):
  buttons  D-pad -> D-pad, A/B/X/Y -> A/B/X/Y               (default)
  left     D-pad -> left stick, A/B/X/Y stay buttons
  sticks   D-pad -> left stick, A/B/X/Y -> right stick (X up, A right, B down, Y left)
On this console the left stick is wired to the D-pad and the right stick to
A/B/X/Y, so the sticks drive these the same way.

Codecs: "raw" sends only the changed RGB565 pixels, losslessly
(tfcodec); text stays sharp and the console decodes it almost for free. Full
screen changes cost up to 600 KB per 640x480 frame, so fast motion drops to
~10 fps. "jpeg" keeps ~12 fps at 640x480 or ~27 fps at 320x240 regardless of
motion, with JPEG artefacts.

Needs: ffmpeg, remote control on the console (tfmtp.remote), cubegm/tfview,
and for the gamepad the ViGEmBus driver + `pip install vgamepad`.
The console must be in the TreeFrogUI menu when you start (tfview is launched
like any TreeFrog app). Quit: Ctrl+C here, or hold SELECT+START for 1.5 s on
the console.
"""
import argparse
import ctypes
import os
import shutil
import struct
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r36 import R36  # noqa: E402

FFMPEG = os.environ.get('FFMPEG') or shutil.which('ffmpeg') or r'C:\Program Files\ffmpeg-7.1-full_build\bin\ffmpeg.exe'
TFVIEW = '/mnt/sdcard/cubegm/tfview'
LAUNCH = '/mnt/sdcard/cubegm/frogui_launch.txt'

# joy_key bits (frogui/keymap.txt defaults on the GB350)
BITS = dict(SELECT=0, START=3, UP=4, RIGHT=5, DOWN=6, LEFT=7, L2=8, R2=9, L1=10, R1=11, X=12, A=13, B=14, Y=15,
            FN=16)   # L2/R2/FN measured on the GB350 (TreeFrog's keymap lists L2/R2 as absent)


class Grabber(threading.Thread):
    """ffmpeg screen capture -> JPEG frames or raw RGB565 frames; keeps only the newest frame."""

    def __init__(self, args):
        super().__init__(daemon=True)
        w, h = args.size.split('x')
        self.w, self.h = int(w), int(h)
        self.codec = args.codec
        src = []
        if args.crop:
            x, y, cw, ch = [int(v) for v in args.crop.split(',')]
            src = ['-offset_x', str(x), '-offset_y', str(y), '-video_size', '%dx%d' % (cw, ch)]
        src += ['-i', 'title=' + args.window] if args.window else ['-i', 'desktop']
        vf = ('scale=%s:%s:force_original_aspect_ratio=decrease:flags=lanczos,'
              'pad=%s:%s:(ow-iw)/2:(oh-ih)/2' % (w, h, w, h))
        if self.codec == 'jpeg':     # auto and raw both capture raw RGB565
            out = ['-q:v', str(args.quality), '-f', 'image2pipe', '-c:v', 'mjpeg', '-']
        else:
            out = ['-pix_fmt', 'rgb565le', '-f', 'rawvideo', '-']
        cmd = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-fflags', 'nobuffer', '-flags', 'low_delay',
               '-probesize', '32', '-f', 'gdigrab', '-draw_mouse', '1',
               '-framerate', str(args.fps)] + src + ['-vf', vf, '-flush_packets', '1'] + out
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
        self.lock = threading.Lock()
        self.frame, self.count = None, 0
        self.last_raw = None

    def _put(self, f):
        with self.lock:
            self.frame = f
            self.count += 1

    def run(self):
        buf = b''
        fsize = self.w * self.h * 2
        while True:
            raw = self.codec != 'jpeg'
            chunk = self.p.stdout.read(fsize if raw else 65536)
            if not chunk:
                break
            buf += chunk
            if raw:
                while len(buf) >= fsize:
                    self._put(buf[:fsize])
                    buf = buf[fsize:]
                continue
            while True:
                s = buf.find(b'\xff\xd8')
                e = buf.find(b'\xff\xd9', s + 2) if s >= 0 else -1
                if s < 0 or e < 0:
                    break
                self._put(buf[s:e + 2])
                buf = buf[e + 2:]

    def take(self):
        with self.lock:
            f, self.frame = self.frame, None
            return f

    def stop(self):
        try:
            self.p.kill()
        except OSError:
            pass


class RawEncoder:
    """Lossless RGB565 delta coder (tfcodec.dll, the same code tfview decodes)."""

    def __init__(self, w, h, key_every=5.0):
        self.dll = ctypes.CDLL(os.path.join(HERE, 'tfcodec.dll'))
        self.dll.tfc_encode.restype = ctypes.c_size_t
        self.dll.tfc_encode.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_void_p, ctypes.c_size_t]
        self.dll.tfc_downscale2.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        self.w, self.h = w, h
        n = w * h
        self.prev = (ctypes.c_uint16 * n)()
        self.cap = n * 2 + n // 8 + 64
        self.out = (ctypes.c_uint8 * self.cap)()
        self.key_every, self.last_key = key_every, 0.0

    def encode(self, frame):
        """returns (fmt, payload): fmt 2 = key frame, 3 = delta frame"""
        now = time.time()
        key = now - self.last_key >= self.key_every
        n = self.dll.tfc_encode(frame, None if key else self.prev, self.w, self.h, self.out, self.cap)
        if key:
            ctypes.memmove(self.prev, frame, self.w * self.h * 2)
            self.last_key = now
        if n == 0:                      # should not happen with TFC_MAX_BYTES; force a key frame next
            self.last_key = 0.0
            return None, b''
        return (2 if key else 3), ctypes.string_at(self.out, n)


class AutoEncoder:
    """Lossless while the picture is mostly still, 320x240 JPEG while much of it moves."""

    HI, LO, CALM = 0.10, 0.03, 3          # changed-pixel fractions, calm frames before going back

    def __init__(self, w, h, jpeg_quality=80):
        import numpy as np
        from PIL import Image
        self.np, self.Image = np, Image
        self.raw = RawEncoder(w, h)
        self.w, self.h, self.q = w, h, jpeg_quality
        self.last = None
        self.mode, self.calm = 'raw', 0
        self.n_raw = self.n_jpeg = 0

    def _jpeg(self, frame):
        np = self.np
        small = (ctypes.c_uint16 * ((self.w // 2) * (self.h // 2)))()
        self.raw.dll.tfc_downscale2(frame, self.w, self.h, small)          # C, ~1 ms
        a = np.frombuffer(small, dtype='<u2').reshape(self.h // 2, self.w // 2)
        rgb = np.empty((self.h // 2, self.w // 2, 3), np.uint8)
        rgb[..., 0] = (a >> 8) & 0xF8
        rgb[..., 1] = (a >> 3) & 0xFC
        rgb[..., 2] = (a << 3) & 0xF8
        import io
        bio = io.BytesIO()
        self.Image.fromarray(rgb, 'RGB').save(bio, 'JPEG', quality=self.q, subsampling=2)
        return bio.getvalue()

    def encode(self, frame):
        np = self.np
        cur = np.frombuffer(frame, dtype='<u2')
        frac = 1.0 if self.last is None else float(np.count_nonzero(cur != self.last)) / cur.size
        self.last = cur.copy()
        if self.mode == 'raw' and frac > self.HI and self.raw.last_key and frac < 1.0:
            self.mode, self.calm = 'jpeg', 0
        elif self.mode == 'jpeg':
            self.calm = self.calm + 1 if frac < self.LO else 0
            if self.calm >= self.CALM:
                self.mode = 'raw'
                self.raw.last_key = 0.0          # the console needs a key frame after JPEG
        if self.mode == 'jpeg':
            self.n_jpeg += 1
            return 1, self._jpeg(frame), 'jpeg 320x240'
        self.n_raw += 1
        fmt, payload = self.raw.encode(frame)
        return fmt, payload, 'lossless'


class Pad:
    """Console buttons -> virtual Xbox 360 controller (ViGEmBus via vgamepad)."""

    def __init__(self):
        import vgamepad as vg
        self.vg = vg
        self.pad = vg.VX360Gamepad()
        B = vg.XUSB_BUTTON
        self.map = {
            'A': B.XUSB_GAMEPAD_A, 'B': B.XUSB_GAMEPAD_B, 'X': B.XUSB_GAMEPAD_X, 'Y': B.XUSB_GAMEPAD_Y,
            'L1': B.XUSB_GAMEPAD_LEFT_SHOULDER, 'R1': B.XUSB_GAMEPAD_RIGHT_SHOULDER,
            'START': B.XUSB_GAMEPAD_START, 'SELECT': B.XUSB_GAMEPAD_BACK,
            'FN': B.XUSB_GAMEPAD_LEFT_THUMB,                     # FN -> L3 (left stick click)
            'UP': B.XUSB_GAMEPAD_DPAD_UP, 'DOWN': B.XUSB_GAMEPAD_DPAD_DOWN,
            'LEFT': B.XUSB_GAMEPAD_DPAD_LEFT, 'RIGHT': B.XUSB_GAMEPAD_DPAD_RIGHT,
        }
        self.last = None
        self.mode = 'buttons'

    MODES = ('buttons', 'left', 'sticks')

    def cycle(self):
        self.mode = self.MODES[(self.MODES.index(self.mode) + 1) % len(self.MODES)]
        self.last = None
        return self.mode

    @staticmethod
    def _axis(keys, neg, pos):
        return (32767 if keys >> BITS[pos] & 1 else 0) - (32767 if keys >> BITS[neg] & 1 else 0)

    def update(self, keys):
        if keys == self.last:
            return
        as_left = self.mode in ('left', 'sticks')
        as_right = self.mode == 'sticks'
        skip = set()
        if as_left:
            skip |= {'UP', 'DOWN', 'LEFT', 'RIGHT'}
        if as_right:
            skip |= {'X', 'A', 'B', 'Y'}
        for name, bit in BITS.items():
            if name not in self.map:
                continue
            if keys >> bit & 1 and name not in skip:
                self.pad.press_button(button=self.map[name])
            else:
                self.pad.release_button(button=self.map[name])
        lx = self._axis(keys, 'LEFT', 'RIGHT') if as_left else 0
        ly = self._axis(keys, 'DOWN', 'UP') if as_left else 0
        rx = self._axis(keys, 'Y', 'A') if as_right else 0          # right stick: Y left, A right
        ry = self._axis(keys, 'B', 'X') if as_right else 0          #              B down, X up
        self.pad.left_trigger(value=255 if keys >> BITS['L2'] & 1 else 0)     # L2 -> LT
        self.pad.right_trigger(value=255 if keys >> BITS['R2'] & 1 else 0)    # R2 -> RT
        self.pad.left_joystick(x_value=lx, y_value=ly)
        self.pad.right_joystick(x_value=rx, y_value=ry)
        self.pad.update()
        self.last = keys

    def close(self):
        try:
            self.pad.reset(); self.pad.update()
        except Exception:
            pass


MODE_TEXT = {'buttons': 'PAD: buttons (D-pad + ABXY)',
             'left': 'PAD: left stick = D-pad',
             'sticks': 'PAD: both sticks (D-pad + ABXY)'}


def burn_osd(frame, w, h, text):
    """Draw a banner with `text` into a raw RGB565 frame (bytes) - shown on the console."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    a = np.frombuffer(frame, dtype='<u2').reshape(h, w)
    rgb = np.empty((h, w, 3), np.uint8)
    rgb[..., 0] = (a >> 8) & 0xF8
    rgb[..., 1] = (a >> 3) & 0xFC
    rgb[..., 2] = (a << 3) & 0xF8
    img = Image.fromarray(rgb, 'RGB')
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arialbd.ttf', max(14, h // 20))
    except OSError:
        font = ImageFont.load_default()
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    x0, y0 = (w - tw) // 2 - 12, h // 12
    d.rectangle([x0, y0, x0 + tw + 24, y0 + th + 16], fill=(0, 0, 0))
    d.text((x0 + 12, y0 + 6 - box[1]), text, font=font, fill=(80, 255, 80))
    r = np.asarray(img).astype(np.uint16)
    out = ((r[..., 0] & 0xF8) << 8) | ((r[..., 1] & 0xFC) << 3) | (r[..., 2] >> 3)
    return out.astype('<u2').tobytes()


def pressed(keys):
    return '+'.join(n for n, b in BITS.items() if keys >> b & 1) or '-'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--size', default='640x480', help='stream size, e.g. 640x480 or 320x240')
    ap.add_argument('--codec', choices=('auto', 'raw', 'jpeg'), default='auto',
                    help='auto (default): lossless when still, 320x240 JPEG when moving; raw; jpeg')
    ap.add_argument('--pad-mode', choices=('buttons', 'left', 'sticks'), default='buttons')
    ap.add_argument('--crop', help='capture only this desktop region: x,y,w,h')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--quality', type=int, default=3, help='JPEG quality 2 (best) .. 31 (worst)')
    ap.add_argument('--window', help='capture one window by its title instead of the whole desktop')
    ap.add_argument('--no-pad', action='store_true', help='do not create a virtual gamepad')
    ap.add_argument('--seconds', type=float, default=0, help='stop after N seconds (0 = until Ctrl+C)')
    ap.add_argument('--inflight', type=int, default=1, help='frames sent but not yet shown (1 = lowest latency)')
    ap.add_argument('--keep', action='store_true', help='leave tfview running on the console when stopping')
    args = ap.parse_args(argv)

    pad = None
    if not args.no_pad:
        try:
            pad = Pad()
            while pad.mode != args.pad_mode:
                pad.cycle()
            print('gamepad: virtual Xbox 360 controller connected, mode "%s" (SELECT+R1 on the console cycles modes)' % pad.mode)
        except Exception as e:
            print('gamepad unavailable (%s) - install the ViGEmBus driver and `pip install vgamepad`; video only' % e)

    r = R36()
    ready = r.run('[ -f /tmp/tfview.ready ] && echo yes || echo no')[1].strip() == b'yes'
    if not ready:
        print('starting tfview on the console (the console must be in the TreeFrogUI menu)...')
        r.run('printf "standalone\\n%s\\n\\n" > %s' % (TFVIEW, LAUNCH))
        for _ in range(40):
            time.sleep(0.25)
            if r.run('[ -f /tmp/tfview.ready ] && echo yes || echo no')[1].strip() == b'yes':
                break
        else:
            print('tfview did not start: is the console in the menu (not in a game)?')
            return 1
    job = r.exec_start('cat /tmp/tfview.out & exec cat > /tmp/tfview.in', stdin=True)

    g = Grabber(args)
    enc = RawEncoder(g.w, g.h) if args.codec == 'raw' else AutoEncoder(g.w, g.h) if args.codec == 'auto' else None
    g.start()
    print('streaming %s %s at up to %d fps (Ctrl+C to stop; hold SELECT+START 1.5 s on the console)' % (args.size, args.codec, args.fps))
    sent = sent_bytes = shown = 0
    t0 = t_stat = time.time()
    keys, kbuf, quit_reason, combo_held, cur_codec = 0, b'', None, False, '-' 
    sent_at = {}                     # frame number -> send time, for the latency figure
    shown_base = None
    osd_text, osd_until = None, 0.0
    last_keys_print = None
    lat = []
    try:
        while True:
            # 1. status from the console: buttons + how many frames it has shown
            wait = 0 if sent - shown < args.inflight else 5
            data, state, code, eof, pending = r.job_read(job, 4096, wait)
            if state:
                quit_reason = 'console side ended (SELECT+START)'
                break
            kbuf += data
            while True:
                i = kbuf.find(b'TFK')
                if i < 0:
                    kbuf = kbuf[-3:]
                    break
                if len(kbuf) - i < 16:
                    kbuf = kbuf[i:]
                    break
                magic, keys, val, ms = struct.unpack_from('<4sIII', kbuf, i)
                kbuf = kbuf[i + 16:]
                if magic == b'TFK2' and shown_base is None:
                    shown_base = val - sent        # tfview may already have shown frames of an earlier session
                if magic == b'TFK2':
                    val -= shown_base
                if magic == b'TFK2' and val > shown:
                    now = time.time()
                    for k in range(shown + 1, val + 1):
                        t = sent_at.pop(k, None)
                        if t is not None:
                            lat.append(now - t)
                    shown = val
                if pad:
                    combo = (1 << BITS['SELECT']) | (1 << BITS['R1'])
                    if keys & combo == combo and not combo_held:
                        print('\ngamepad mode: %s' % pad.cycle())
                        osd_text, osd_until = MODE_TEXT[pad.mode], time.time() + 1.5
                    combo_held = keys & combo == combo
                    pad.update(keys & ~combo if combo_held else keys)
            # 2. send the newest captured frame, but only if the console has caught up
            if sent - shown < args.inflight:
                f = g.take()
                if f is None and osd_text and g.last_raw is not None:
                    f = g.last_raw                     # still desktop: re-send so the banner shows/clears
                if f is not None and g.codec != 'jpeg':
                    g.last_raw = f
                    if osd_until > time.time():
                        f = burn_osd(f, g.w, g.h, osd_text)
                    elif osd_text:
                        osd_text = None                # this clean frame removes the banner
                if f is not None:
                    if isinstance(enc, AutoEncoder):
                        fmt, payload, cur_codec = enc.encode(f)
                    elif enc:
                        (fmt, payload), cur_codec = enc.encode(f), 'lossless'
                    else:
                        fmt, payload, cur_codec = 1, f, 'jpeg'
                    if fmt:
                        pkt = struct.pack('<4sIHHB3x', b'TFV1', len(payload), g.w, g.h, fmt) + payload
                        r.job_write(job, pkt)
                        sent += 1
                        sent_bytes += len(pkt)
                        sent_at[sent] = time.time()
                else:
                    time.sleep(0.002)
            now = time.time()
            if args.seconds and now - t0 >= args.seconds:
                quit_reason = 'time limit'
                break
            if now - t_stat >= 2 or keys != last_keys_print:
                last_keys_print = keys
                dt = now - t0
                l = sorted(lat[-60:])
                lt = ('send->shown %3.0f ms (max %3.0f)' % (1000 * l[len(l) // 2], 1000 * l[-1])) if l else 'send->shown -'
                print('\r%5.0fs  %d frames (%.1f fps, %.2f MB/s)  %s  %-12s pad %-7s buttons %-28s' %
                      (dt, shown, shown / dt, sent_bytes / dt / 2**20, lt, cur_codec,
                       pad.mode if pad else '-', pressed(keys) + ' raw=0x%04x' % keys), end='', flush=True)
                t_stat = now
    except KeyboardInterrupt:
        quit_reason = 'Ctrl+C'
    finally:
        print('\nstopping (%s)' % (quit_reason or 'error'))
        g.stop()
        if not args.keep:
            try:
                r.job_write(job, struct.pack('<4sIHHB3x', b'TFV1', 0, 0, 0, 0))   # ask tfview to quit
            except Exception:
                pass
        r.job_signal(job, 9)
        r.job_signal(job, 0)
        if pad:
            pad.close()
        r.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
