#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Vivado impl reports into a Markdown resource/timing table.

Vivado 2026.1 report layouts used here:
  * *_utilization_placed.rpt: lines like
      |   LUT as Logic             | 35236 | 0 | 0 | 53200 | 66.23 |
      |   Register as Flip Flop    | 41438 | 0 | 0 | 106400 | 38.95 |
      | Block RAM Tile    | 81.5 | 0 | 0 | 140 | 58.21 |
      | DSPs           |  140 | 0 | 0 | 220 | 63.64 |
  * *_timing_summary_routed.rpt: "Intra Clock Table" section, e.g.
      clk_fpga_0   0.134  0.000  0  108424  0.023  0.000  0  108424 ...
      (columns: clock, WNS, TNS, TNS failing, TNS total, WHS, ...)

Usage:
    python parse_vivado_reports.py --util U.rpt --timing T.rpt [--out table.md]
"""
import argparse


def parse_util(path):
    out = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if '|' not in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 7:
                continue
            name = parts[1]
            for key in ('LUT as Logic', 'Register as Flip Flop',
                        'Block RAM Tile', 'DSPs'):
                if name == key and key not in out:
                    try:
                        out[key] = (float(parts[2]), float(parts[5]),
                                    float(parts[6]))
                    except ValueError:
                        pass
    return out


def parse_timing(path):
    """Return {clock: (WNS, WHS)} from the Intra Clock Table."""
    out = {}
    in_table = False
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if 'Intra Clock Table' in line:
                in_table = True
                continue
            if not in_table:
                continue
            s = line.strip()
            if not s:
                if out:
                    break
                continue
            if s.startswith('-') or s.startswith('Clock'):
                continue
            parts = s.split()
            if len(parts) < 6:
                continue
            # first token is the clock name; skip header-ish rows
            try:
                wns = float(parts[1])
                whs = float(parts[5])
            except (ValueError, IndexError):
                continue
            out[parts[0]] = (wns, whs)
    return out


def fmt_pct(x):
    return '%.2f%%' % x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--util', required=True)
    ap.add_argument('--timing', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--clocks', nargs='*', default=None,
                    help='clocks to include in the timing table')
    args = ap.parse_args()

    util = parse_util(args.util)
    timing = parse_timing(args.timing)
    if not util:
        raise SystemExit('no utilization rows parsed from %s' % args.util)
    if not timing:
        raise SystemExit('no Intra Clock Table rows parsed from %s'
                         % args.timing)

    lines = ['## Resource utilization (placed)', '',
             '| Resource | Used | Total | % |',
             '|---|---:|---:|---:|']
    order = ['LUT as Logic', 'Register as Flip Flop',
             'Block RAM Tile', 'DSPs']
    for k in order:
        if k in util:
            used, total, pct = util[k]
            lines.append('| %s | %s | %s | %s |'
                         % (k, ('%g' % used), ('%g' % total), fmt_pct(pct)))
    lines += ['', '## Timing (routed, Intra Clock Table)', '',
              '| Clock | WNS (ns) | WHS (ns) |',
              '|---|---:|---:|']
    clocks = args.clocks or sorted(timing)
    for c in clocks:
        if c in timing:
            wns, whs = timing[c]
            flag = ' **FAIL**' if (wns < 0 or whs < 0) else ''
            lines.append('| %s | %+.3f | %+.3f%s |' % (c, wns, whs, flag))
    text = '\n'.join(lines) + '\n'
    print(text)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text)
        print('-> %s' % args.out)
    bad = [c for c, (w, h) in timing.items() if w < 0 or h < 0]
    return 2 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
