#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small, project-independent helpers for stable VDMA capture/display on PYNQ.

Set FRAME_BYTES / FRAME_SHAPE to your video geometry.  No pynq import at module
top, so the pure functions can be reviewed/tested on a PC with fake buffers.
"""
import time

import numpy as np

FRAME_SHAPE = (480, 640, 3)          # H, W, BPP (BGR in this project)
FRAME_BYTES = int(np.prod(FRAME_SHAPE))


def read_store(buf, store=0, frame_bytes=FRAME_BYTES,
               shape=FRAME_SHAPE):
    """Read one frame store.  Not tear-safe by itself -- use read_store_stable."""
    off = int(store) * int(frame_bytes)
    return np.array(buf[off:off + frame_bytes],
                    dtype=np.uint8).reshape(shape)


def read_store_stable(buf, store=0, frame_bytes=FRAME_BYTES,
                      shape=FRAME_SHAPE, tries=5, poll=0.01):
    """Read twice and accept only when both reads are byte-identical.

    DMA rewrites a store every ~105 ms (28.5 fps / 3 stores); two reads ~6 ms
    apart are either both from the same completed frame or at least one is torn.
    Returns (frame, ok); ok=False means retries were exhausted.
    """
    prev = read_store(buf, store, frame_bytes, shape)
    for _ in range(max(0, tries)):
        time.sleep(poll)
        cur = read_store(buf, store, frame_bytes, shape)
        if np.array_equal(prev, cur):
            return cur, True
        prev = cur
    return prev, False


def wait_valid_frame(buf, store=0, timeout=2.0, min_max=16, **kw):
    """Wait for a stable non-black frame; returns None on timeout.

    ⚠️ A stable all-zero stale buffer also passes "read twice identical".
       This function only checks max>=min_max; it does NOT prove DMA is running.
    """
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        fr, ok = read_store_stable(buf, store, tries=3, **kw)
        if ok and int(fr.max()) >= min_max:
            return fr
        time.sleep(0.02)
    return None


def read_mm2s_addrs(mmio, base=0x5C, n=3):
    """Read the MM2S frame-store start-address registers (default 3 stores)."""
    return [mmio.read(base + 4 * i) for i in range(n)]


def display_selftest(present, shape=FRAME_SHAPE, seconds=0.6):
    """Push white/black/white-text/white through the SAME path used at runtime.

    `present` is a callable accepting an (H,W,3) uint8 image.  If the screen
    stays black, check monitor input, cable, then main.py -- do not conclude
    "the path is fine" from a CPU readback.
    """
    import cv2
    print('HDMI selftest: white -> black -> white/black text -> white')
    time.sleep(0.8)
    frames = [np.full(shape, 255, np.uint8),
              np.zeros(shape, np.uint8)]
    f = np.full(shape, 255, np.uint8)
    cv2.putText(f, 'HDMI OK', (90, shape[0] // 2), cv2.FONT_HERSHEY_SIMPLEX,
                3.0, (0, 0, 0), 8, cv2.LINE_AA)
    frames += [f, np.full(shape, 255, np.uint8)]
    for img in frames:
        present(img)
        time.sleep(seconds)
    print('HDMI selftest done')


def shutdown(vdma, disp_ctrl=None, buffers=()):
    """Stop DMA/display and free buffers.  NEVER skip this on exit."""
    try:
        vdma.stop()
    except Exception as e:
        print('WARN vdma.stop:', e)
    if disp_ctrl is not None:
        try:
            disp_ctrl.stop()
        except Exception as e:
            print('WARN disp_ctrl.stop:', e)
    for b in buffers:
        if b is None:
            continue
        for meth in ('freebuffer', 'free', 'release'):
            if hasattr(b, meth):
                try:
                    getattr(b, meth)()
                    break
                except Exception:
                    pass
