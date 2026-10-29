#!/usr/bin/env python3
"""
Measure how many units the game program can move (#943, part of #398): the RCON commands per second and the server
tick time with 200, 500 and 1000 moving units.

Usage:
    python3 tools/measure_units.py [--units 200,500,1000] [--scenario battle] [--seconds 30] [--period 5]
    python3 tools/measure_units.py --world WORLD      # a converted world (the tool works on a copy)
    python3 tools/measure_units.py --reveal normal    # also the fog of war of the units (game/fog.py) each second

The tool converts the scenario (`tools/scenarios.py`, as `tools/tick_cost.py`) and starts the Paper server of the
game program without a client. It summons husks (the mob of most units) on free ground cells near the map center,
and adds units up to each count of --units in the same server. Each unit gets the walk speed of a militia
(`ai.speed_command`) and every --period seconds its own `aoe moveto` (`ai.move`, Minecraft path finding of the Paper
plugin) to a random free cell near its home. Minecraft measures the ticks itself (`/tick query`, the last 100 ticks):
no own profiler. The commands per second are the moveto commands divided by the time to send them.
With `--reveal normal` (#1389) half of the units are own soldiers of player 1 and half enemies of player 2, and
fog.tick of a Gather hides the enemies out of their sight each second; the column "fog ms" is its mean time.
With `--fight` (#3325) the units of player 1 (even) and player 2 (odd) attack each other: every --period seconds unit i
gets `aoe attack` (`ai.attack`, the Minecraft attack goal) on its neighbour i ^ 1, and the tool summons each dead unit
again at its home, so that the count stays. The column "orders that reached a unit" then counts the attack orders.
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
    fog = any("fog" in r for r in rows)
    lines = ["units | commands per second | mean tick ms | P99 tick ms | ticks per second | orders that reached a unit"
             + " | fog ms" * fog, "---|---|---|---|---|---" + "|---" * fog]
    return "\n".join(lines + [f"{r['units']} | {r['rate']:.0f} | {r['mean']:.2f} | {r['p99']:.2f} | {tps(r['mean']):.1f} | "
                              f"{r['moved']:.0%}" + (f" | {r['fog']:.1f}" if fog else "") for r in rows])


def summon(game, m, i, x, z):
    """Summon unit i of the measurement at free cell (x, z), without AI until its first order."""
    _, ints = unit_uuid(i)
    game.command(f"summon minecraft:husk {x + 0.5} {m.y(x, z)} {z + 0.5} {{UUID:[I;{','.join(map(str, ints))}],"
                 f"Tags:[\"{TAG}\"],NoAI:1b,PersistenceRequired:1b,Silent:1b}}")


def measure(world, counts, seconds=30, period=5.0, version=None, log=print, reveal="all", fight=False):
    """One row per count of units: {"units", "rate", "mean", "p99", "moved"} (moved: the share of the orders that
    reached their unit), with reveal "normal" also "fog" (ms of one fog.tick). The units of a count stay for the
    next one."""
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
        g, fogs = (gather.Gather(game, data) if reveal == "normal" else None), []
        if fight:
            for p in (1, 2):                                       # no unit attacks its own side (sameTeam)
                game.command(f"team add p{p}")
        for count in counts:
            for i in range(len(units), count):
                s, x, z = unit_uuid(i)[0], *spots[i]
                summon(game, m, i, x, z)
                units.append((s, x, z))
                if g or fight:                                     # even: own soldiers, odd: enemies (fog.py)
                    game.command(f"team join p{1 + i % 2} {s}")
                if g:
                    (g.soldiers if i % 2 == 0 else g.enemies)[s] = NAME
            sent, moved, dead, busy, samples, t_end = 0, 0, 0, 0.0, [], time.monotonic() + seconds
            while time.monotonic() < t_end:
                t0 = time.monotonic()
                for i, (s, x, z) in enumerate(units if fight else []):
                    if "passed" not in game.command(f"execute if entity {s}"):
                        summon(game, m, i, x, z)                   # a dead unit comes back: the count stays
                        dead += 1
                        game.command(f"team join p{1 + i % 2} {s}")
                    foe = units[i ^ 1][0] if i ^ 1 < len(units) else units[i - 1][0]
                    moved += "Attack: 1 " in ai.attack(game, [s], [NAME], T, foe)[0]
                for s, x, z in [] if fight else units:
                    for _ in range(8):                             # a free cell near the home
                        tx, tz = x + int(rng.integers(-RADIUS, RADIUS + 1)), z + int(rng.integers(-RADIUS, RADIUS + 1))
                        if m.free(tx, tz):
                            break
                    else:
                        tx, tz = x, z
                    moved += "Moved 1 " in ai.move(game, s, NAME, T, tx + 0.5, m.y(tx, tz), tz + 0.5)
                sent += (3 if fight else 2) * len(units)           # the speed and the order (and the alive test)
                busy += time.monotonic() - t0
                while g and period - (time.monotonic() - t0) > 1.0:
                    t1 = time.monotonic()
                    vars(g).get("fog", {})["at"] = None            # one update each second here
                    gather.fog.tick(g)
                    fogs.append(time.monotonic() - t1)
                    time.sleep(max(0.0, 1.0 - (time.monotonic() - t1)))
                time.sleep(max(0.0, period - (time.monotonic() - t0)))
                samples.append(parse(game.command("tick query")))
            row = {"units": count, "rate": sent / busy if busy else 0.0,
                   "mean": statistics.median(s[0] for s in samples), "p99": max(s[1] for s in samples),
                   "moved": moved / (sent / (3 if fight else 2)) if sent else 0.0} | ({"fog": 1000 * statistics.mean(fogs)} if fogs else {})
            if log:
                log(f"{count} units: {row['rate']:.0f} commands/s, mean {row['mean']:.2f} ms, P99 {row['p99']:.2f} ms, "
                    f"orders that reached a unit {row['moved']:.0%}" + (f", dead units {dead}" if fight else ""))
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
    ap.add_argument("--reveal", choices=["normal", "all"], default="all", help="normal: also the fog of war of the "
                    "units each second (game/fog.py, #1389); default all: no fog, as game/run.py --reveal all")
    ap.add_argument("--fight", action="store_true", help="the units of player 1 and 2 attack each other instead of "
                    "walking (aoe attack, #3325); dead units come back")
    a = ap.parse_args(argv)
    counts = sorted(int(c) for c in a.units.split(","))
    import mc_check
    import tick_cost
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        world = shutil.copytree(a.world, os.path.join(tmp, "World")) if a.world else tick_cost.convert(a.scenario, tmp)
        rows = measure(world, counts, a.seconds, a.period, a.version, reveal=a.reveal, fight=a.fight)
    print(report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
