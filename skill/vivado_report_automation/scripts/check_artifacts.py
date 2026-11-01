#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check the final PYNQ overlay pair: existence, size, md5.

    python check_artifacts.py --bit design_1.bit --hwh design_1.hwh \
        --expect-bit-md5 <hash> --expect-hwh-md5 <hash>

Exit 0 = all present and expected hashes match; 1 = missing/size 0; 2 = md5 mismatch.
"""
import argparse
import hashlib
import os


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bit', required=True)
    ap.add_argument('--hwh', required=True)
    ap.add_argument('--expect-bit-md5')
    ap.add_argument('--expect-hwh-md5')
    args = ap.parse_args()

    rc = 0
    for name, path, expect, what in (
            ('bit', args.bit, args.expect_bit_md5, 'bitstream'),
            ('hwh', args.hwh, args.expect_hwh_md5, 'handoff')):
        print('%s: %s' % (what, path))
        if not os.path.isfile(path):
            print('  **MISSING**')
            rc = max(rc, 1)
            continue
        size = os.path.getsize(path)
        digest = md5(path)
        print('  size=%d  md5=%s' % (size, digest))
        if size == 0:
            print('  **EMPTY FILE**')
            rc = max(rc, 1)
        if expect and digest != expect:
            print('  **MD5 MISMATCH** expected %s' % expect)
            rc = max(rc, 2)
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
