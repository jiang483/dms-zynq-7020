#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HLS accelerator driver template (PYNQ, Zynq-7000).

Assumes the IP was generated with:
    #pragma HLS INTERFACE m_axi port=in  bundle=gmem depth=N_IN
    #pragma HLS INTERFACE m_axi port=out bundle=gmem depth=N_OUT
    #pragma HLS INTERFACE s_axilite port=in  bundle=control
    #pragma HLS INTERFACE s_axilite port=out bundle=control
    #pragma HLS INTERFACE s_axilite port=return bundle=control
    #pragma HLS INTERFACE ap_ctrl_hs port=return

Register map produced by Vitis HLS 2026.1 (verify against the generated
x<ip>_hw.h; offsets are stable, names are not):

    0x00 AP_CTRL  bit0 start / bit1 done / bit2 idle / bit3 ready
    0x04 GIE  0x08 IER  0x0c ISR
    0x10 in_ptr  lo   0x14 hi
    0x1c out_ptr lo   0x20 hi

Do NOT use ap_ctrl_none: scalar inputs are only latched at reset and ap_done
never asserts.  Do NOT forget to free the CMA buffers on exit.
"""
import time

import numpy as np

try:
    from pynq import allocate, MMIO
    _HAVE_PYNQ = True
except ImportError:
    allocate = MMIO = None
    _HAVE_PYNQ = False

AP_CTRL = 0x00
PATCH_IN = 0x10
LOGITS_OUT = 0x1c
PTR_HI = 0x04
AP_START = 1 << 0
AP_DONE = 1 << 1


class HlsAccel:
    N_IN = 1024          # <-- set to your input element count
    N_OUT = 3            # <-- set to your output element count
    TIMEOUT_S = 2.0

    def __init__(self, ip):
        self.ip = ip
        self.mm = getattr(ip, 'mmio', None)
        if self.mm is None:
            desc = getattr(ip, 'description', {}) or {}
            self.mm = MMIO(desc['phys_addr'], desc.get('addr_range', 0x10000))
        self.inp = allocate(shape=(self.N_IN,), dtype=np.int8)
        self.out = allocate(shape=(self.N_OUT,), dtype=np.int32)
        self._set_ptr(PATCH_IN, self._phys(self.inp))
        self._set_ptr(LOGITS_OUT, self._phys(self.out))
        self.n = 0
        self.t_total = 0.0

    @staticmethod
    def _phys(buf):
        for a in ('physical_address', 'device_address'):
            if hasattr(buf, a):
                return int(getattr(buf, a))
        raise AttributeError('buffer has no physical address')

    def _set_ptr(self, off, addr):
        self.mm.write(off, addr & 0xFFFFFFFF)
        self.mm.write(off + PTR_HI, (addr >> 32) & 0xFFFFFFFF)

    def read_ptr(self, which):
        off = PATCH_IN if which == 'in' else LOGITS_OUT
        return (self.mm.read(off + PTR_HI) << 32) | self.mm.read(off)

    def infer(self, x):
        flat = np.ascontiguousarray(x, dtype=np.int8).reshape(-1)
        if flat.size != self.N_IN:
            raise ValueError('expected %d int8, got %d' % (self.N_IN, flat.size))
        self.inp[:] = flat
        self.inp.flush()
        t0 = time.perf_counter()
        self.mm.write(AP_CTRL, AP_START)
        deadline = t0 + self.TIMEOUT_S
        while True:
            st = self.mm.read(AP_CTRL)
            if st & AP_DONE:
                break
            if time.perf_counter() > deadline:
                raise TimeoutError('ap_done not set (AP_CTRL=0x%02x)' % st)
        dt = time.perf_counter() - t0
        self.out.invalidate()
        y = np.array(self.out, dtype=np.int64)
        self.n += 1
        self.t_total += dt
        return y, dt

    def close(self):
        for name in ('inp', 'out'):
            buf = getattr(self, name, None)
            if buf is None:
                continue
            for meth in ('freebuffer', 'free', 'release'):
                if hasattr(buf, meth):
                    try:
                        getattr(buf, meth)()
                        break
                    except Exception:
                        pass
            setattr(self, name, None)
