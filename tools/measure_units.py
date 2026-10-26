#!/usr/bin/env python3
"""
Measure how many units the game program can move (#943, part of #398): the RCON commands per second and the server
tick time with 200, 500 and 1000 moving units.

Usage:
    python3 tools/measure_units.py [--units 200,500,1000] [--scenario battle] [--seconds 30] [--period 5]
    python3 tools/measure_units.py --world WORLD      # a converted world (the tool works on a copy)

The tool converts the scenario (`tools/scenarios.py`, as `tools/tick_cost.py`) and starts the Paper server of the
game program without a client. It summons husks (the mob of most units) on free ground cells near the map center,
and adds units up to each count of --units in the same server. Each unit gets the walk speed of a militia
(`ai.speed_command`) and every --period seconds its own `aoe moveto` (`ai.move`, Minecraft path finding of the Paper
plugin) to a random free cell near its home. Minecraft measures the ticks itself (`/tick query`, the last 100 ticks):
no own profiler. The commands per second are the moveto commands divided by the time to send them.
"""
import argparse
import os
import re
import shutil
import statistics
import sys
import tempfile
import time
import uuid

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

TAG = "aoe_bench"
NAME = "MILITIA"                 # the AoE2 unit of the walk speed
RADIUS = 12                      # blocks from its home that a unit walks to
QUERY = re.compile(r"Average time per tick: ([\d.]+)ms.*P99: ([\d.]+)ms", re.S)


def parse(text):
    """(mean ms, P99 ms) from the answer of /tick query."""
    m = QUERY.search(text)
    if not m:
        raise ValueError(f"no tick times in {text!r}")
    return float(m.group(1)), float(m.group(2))


def homes(cells, n, seed=0):
    """n home cells (x, z) from the free cells, nearest to their center first, with no cell twice while there are
    enough cells. Deterministic (seeded)."""
    cells = sorted(cells)
    c = np.mean(cells, axis=0)
    order = np.argsort([(x - c[0]) ** 2 + (z - c[1]) ** 2 for x, z in cells], kind="stable")
    pick = [cells[i] for i in order[:n]]
    rng = np.random.default_rng(seed)
    return pick + [pick[i] for i in rng.integers(0, len(pick), n - len(pick))] if len(pick) < n else pick


def unit_uuid(i):
    """A fixed UUID (string, the 4 signed ints of the NBT int array) for unit i of the measurement."""
    u = uuid.UUID(int=(0x6a6f6230_4000_4000_8000_000000000000 + i))
    return str(u), [((u.int >> (96 - 32 * k)) & 0xFFFFFFFF) - ((u.int >> (127 - 32 * k)) & 1) * (1 << 32) for k in range(4)]


def tps(mean):
    """Ticks per second at a mean tick time (ms): at most 20."""
    return min(20.0, 1000 / mean) if mean > 0 else 20.0


def report(rows):
    lines = ["units | commands per second | mean tick ms | P99 tick ms | ticks per second | orders that reached a unit",
             "---|---|---|---|---|---"]
    return "\n".join(lines + [f"{r['units']} | {r['rate']:.0f} | {r['mean']:.2f} | {r['p99']:.2f} | {tps(r['mean']):.1f} | "
                              f"{r['moved']:.0%}" for r in rows])


def measure(world, counts, seconds=30, period=5.0, version=None, log=print):
    """One row per count of units: {"units", "rate", "mean", "p99", "moved"} (moved: the share of the orders that
    reached their unit). The units of a count stay for the next one."""
    import json

    import ai
    import gather
    import mc_check
    import run
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T, m = data["tile_size"], gather.Map(data)
    cells = [(x, z) for z in range(m.n) for x in range(m.n) if m.free(x, z)]
    spots = homes(cells, max(counts))
    rng, rows, units = np.random.default_rng(1), [], []
    with run.Game(world, version or mc_check.DEFAULT_VERSION) as game:
        game.forceload()
        time.sleep(10)                                             # chunks and entities load in other threads
        for count in counts:
            for i in range(len(units), count):
                s, ints = unit_uuid(i)
                x, z = spots[i]
                game.command(f"summon minecraft:husk {x + 0.5} {m.y(x, z)} {z + 0.5} {{UUID:[I;{','.join(map(str, ints))}],"
                             f"Tags:[\"{TAG}\"],NoAI:1b,PersistenceRequired:1b,Silent:1b}}")
                units.append((s, x, z))
            sent, moved, busy, samples, t_end = 0, 0, 0.0, [], time.monotonic() + seconds
            while time.monotonic() < t_end:
                t0 = time.monotonic()
                for s, x, z in units:
                    for _ in range(8):                             # a free cell near the home
                        tx, tz = x + int(rng.integers(-RADIUS, RADIUS + 1)), z + int(rng.integers(-RADIUS, RADIUS + 1))
                        if m.free(tx, tz):
                            break
                    else:
                        tx, tz = x, z
                    moved += "Moved 1 " in ai.move(game, s, NAME, T, tx + 0.5, m.y(tx, tz), tz + 0.5)
                sent += 2 * len(units)                             # ai.move: the speed and the moveto
                busy += time.monotonic() - t0
                time.sleep(max(0.0, period - (time.monotonic() - t0)))
                samples.append(parse(game.command("tick query")))
            row = {"units": count, "rate": sent / busy if busy else 0.0,
                   "mean": statistics.median(s[0] for s in samples), "p99": max(s[1] for s in samples),
                   "moved": moved / (sent / 2) if sent else 0.0}
            if log:
                log(f"{count} units: {row['rate']:.0f} commands/s, mean {row['mean']:.2f} ms, P99 {row['p99']:.2f} ms, "
                    f"orders that reached a unit {row['moved']:.0%}")
            rows.append(row)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--units", default="200,500,1000", help="comma-separated unit counts (default 200,500,1000)")
    ap.add_argument("--scenario", default="battle", help="a kind of tools/scenarios.py (default battle)")
    ap.add_argument("--world", help="a converted world instead of --scenario")
    ap.add_argument("--seconds", type=float, default=30, help="measure time per count (default 30)")
    ap.add_argument("--period", type=float, default=5.0, help="seconds between two orders of a unit (default 5)")
    ap.add_argument("--version", help="Minecraft version of the server (default: mc_check.DEFAULT_VERSION)")
    a = ap.parse_args(argv)
    counts = sorted(int(c) for c in a.units.split(","))
    import mc_check
    import tick_cost
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        world = shutil.copytree(a.world, os.path.join(tmp, "World")) if a.world else tick_cost.convert(a.scenario, tmp)
        rows = measure(world, counts, a.seconds, a.period, a.version)
    print(report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
