#!/usr/bin/env python3
"""
Measure the time and the peak memory of each phase of a conversion (#690).

Usage:
    python3 tools/measure_convert.py IN.aoe2scenario [--out DIR] [--tile-size 4]

The conversion runs in this process. A thread reads the resident memory (RSS, /proc/self/statm) every 10 ms, and
aoe2mc.TICKS gives the end of each phase: a sample belongs to the phase that ends next. "units" and "chunks" take
turns in the chunk loop: their rows add all their parts. Prints a Markdown table: phase, seconds, peak MB.
"""
import argparse
import contextlib
import io
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402

PAGE = os.sysconf("SC_PAGE_SIZE")


def rss():
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * PAGE


def measure(src, out, period=0.01, **kw):
    """Convert src to out. Returns ({phase: seconds}, {phase: peak RSS in bytes}, total seconds, output text)."""
    samples, stop = [], threading.Event()

    def sample():
        while not stop.is_set():
            samples.append((time.time(), rss()))
            stop.wait(period)
    th = threading.Thread(target=sample, daemon=True)
    text = io.StringIO()
    th.start()
    try:
        with contextlib.redirect_stdout(text):
            aoe2mc.convert(src, out, verbose=True, **kw)
    finally:
        stop.set()
        th.join()
    ticks = list(aoe2mc.TICKS)
    secs, peak = {}, {}
    for (t0, _), (t1, phase) in zip(ticks, ticks[1:]):
        secs[phase] = secs.get(phase, 0.0) + t1 - t0
        inside = [m for t, m in samples if t0 <= t <= t1] or [next((m for t, m in samples if t >= t1), samples[-1][1])]
        peak[phase] = max(peak.get(phase, 0), *inside)                 # a short phase: the next sample
    return secs, peak, ticks[-1][0] - ticks[0][0], text.getvalue()


def table(secs, peak, total):
    rows = ["| Phase | Seconds | Share | Peak RSS (MB) |", "|---|---|---|---|"]
    rows += [f"| {p} | {s:.1f} | {100 * s / total:.0f} % | {peak[p] / 2**20:.0f} |" for p, s in secs.items()]
    slow = max(secs, key=secs.get)
    rows += [f"| total | {total:.1f} | 100 % | {max(peak.values()) / 2**20:.0f} |", "",
             f"Slowest phase: {slow} ({secs[slow]:.1f} s)."]
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario")
    ap.add_argument("--out", help="the world folder (default: a temporary folder, deleted at the end)")
    ap.add_argument("--tile-size", type=int, default=4)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        secs, peak, total, _ = measure(a.scenario, a.out or os.path.join(tmp, "World"), T=a.tile_size)
    print(table(secs, peak, total))


if __name__ == "__main__":
    main()
