#!/usr/bin/env python3
"""
Measure the tick time that the datapack of a converted world costs on a real server (#458, part of #188).

Usage:
    python3 tools/tick_cost.py [--scenario village] [--ambience basic|full] [--seconds 60] [--version 26.3]
    python3 tools/tick_cost.py --world WORLD          # a converted world (the tool works on copies)

The tool converts the scenario (`tools/scenarios.py`), makes a copy of the world without `datapacks/aoe2mc`, and
starts a server without a client on each copy. It forceloads the map, waits until the entities are loaded, and
reads `/tick query` (the mean of the last 100 ticks) every 5 s. It prints the median of the means and the highest
P99 of both worlds and the difference. Minecraft measures the ticks itself: no own profiler.
No player is on the server, so this is the cost of the pack far from players: each line of `aoe2mc:pulse` stops at
its `if entity @a[distance=..16]` (docs/datapack.md).
"""
import argparse
import contextlib
import io
import os
import re
import shutil
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

LIMIT = 2.0                                                       # ms per tick that the pack may cost (#458)
QUERY = re.compile(r"Average time per tick: ([\d.]+)ms.*P99: ([\d.]+)ms", re.S)


def parse(text):
    """(mean ms, P99 ms) from the answer of /tick query."""
    m = QUERY.search(text)
    if not m:
        raise ValueError(f"no tick times in {text!r}")
    return float(m.group(1)), float(m.group(2))


def tick_times(world, seconds=60, warmup=15, version=None):
    """(median of the mean tick times, highest P99) in ms of a server on world, over seconds after warmup."""
    import mc_check
    import run
    with run.Game(world, version or mc_check.DEFAULT_VERSION) as game:
        game.forceload()
        time.sleep(warmup)                                         # chunks and entities load in other threads
        samples = []
        for _ in range(max(1, int(seconds // 5))):
            time.sleep(5)                                          # 100 ticks: a new sample each time
            samples.append(parse(game.command("tick query")))
    return statistics.median(s[0] for s in samples), max(s[1] for s in samples)


def measure(world, seconds=60, version=None):
    """{"with": (mean, p99), "without": (mean, p99), "lines": lines of aoe2mc:pulse} of world and its copy
    without the pack. The copies keep world as it is (the server saves into the world)."""
    import mc_check
    pulse = os.path.join(world, "datapacks", "aoe2mc", "data", "aoe2mc", "function", "pulse.mcfunction")
    if not os.path.exists(pulse):
        raise SystemExit(f"{world} has no aoe2mc datapack (converted with --ambience off?)")
    with open(pulse) as f:
        lines = sum(1 for line in f if line.strip())
    out = {"lines": lines}
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        for key in ("without", "with"):
            copy = os.path.join(tmp, f"World-{key}")
            shutil.copytree(world, copy)
            if key == "without":
                shutil.rmtree(os.path.join(copy, "datapacks", "aoe2mc"))
            out[key] = tick_times(copy, seconds, version=version)
    return out


def convert(kind, folder, ambience="basic"):
    """Make the test scenario kind (tools/scenarios.py) and convert it. Returns the world folder."""
    import scenarios

    import aoe2mc
    src, world = os.path.join(folder, f"{kind}.aoe2scenario"), os.path.join(folder, f"{kind}World")
    with contextlib.redirect_stdout(io.StringIO()):
        scenarios.MAKERS[kind](src)
        aoe2mc.convert(src, world, ambience=ambience)
    return world


def report(r):
    (w, wp), (n, np_) = r["with"], r["without"]
    return (f"aoe2mc:pulse: {r['lines']} lines, every 40 ticks\n"
            f"without the pack: mean {n:.2f} ms per tick, P99 {np_:.2f} ms\n"
            f"with the pack:    mean {w:.2f} ms per tick, P99 {wp:.2f} ms\n"
            f"difference:       {w - n:+.2f} ms per tick (limit {LIMIT:.1f} ms)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="village", help="a kind of tools/scenarios.py (default village)")
    ap.add_argument("--world", help="a converted world instead of --scenario")
    ap.add_argument("--ambience", choices=("basic", "full"), default="basic")
    ap.add_argument("--seconds", type=float, default=60, help="measure time per world (default 60)")
    ap.add_argument("--version", help="Minecraft version of the server (default: mc_check.DEFAULT_VERSION)")
    a = ap.parse_args(argv)
    import mc_check
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        world = a.world or convert(a.scenario, tmp, a.ambience)
        r = measure(world, a.seconds, a.version)
    print(report(r))
    return 0 if r["with"][0] - r["without"][0] < LIMIT else 1


if __name__ == "__main__":
    sys.exit(main())
