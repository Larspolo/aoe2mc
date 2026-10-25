#!/usr/bin/env python3
"""
Measure the gather timing of game/gather.py on a real server and compare it with AoE2 (#289).

Usage:
    python3 tools/measure_gather.py [--distance 10] [--loads 2] [--log OUT.jsonl] [--version 26.3]
    python3 tools/measure_gather.py --read F.jsonl     # only read a log of game/run.py --play --log F.jsonl

The tool makes a flat map with one villager of player 1, a town center and one tree in one row (`--distance`
tiles from the center of the town center), converts it, starts a server without a client, sends the villager to
the tree (no click) and plays in real time until the villager dropped `--loads` loads. Then it prints the measured
walk speed, chop rate and trip time next to the configured values and AoE2. A row is straight, so no step is
diagonal: a diagonal step is 1.41 blocks in one tick.
"""
import argparse
import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

# AoE2 DE empires2_x2_p1.dat, unit 123 VMLUM (lumberjack), per game second (owner's data in #267)
AOE2_SPEED, AOE2_WORK, AOE2_CARRY, NORMAL = 0.8, 0.39, 10, 1.7     # tiles/s, wood/s, wood, game s per real s


def scenario(path, distance=10):
    """A flat grass map: town center at tile (6, 12), the villager next to it, a tree distance tiles east."""
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.players import PlayerId
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(max(24, 6 + distance + 6))
    um = scn.unit_manager
    um.add_unit(PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=6, y=12)
    um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=9.5, y=12.5)
    um.add_unit(PlayerId.GAIA, OtherInfo.TREE_OAK.ID, x=6 + distance + 0.5, y=12.5)
    return scenarios.save(scn, path, "measure.aoe2scenario")


def analyze(events):
    """Measured values of a log (list of event dicts): walk speed (blocks/s), chop rate (wood/s), trip time (s,
    from drop to drop) and blocks per trip. A value is None when the log has no complete segment for it.
    Each segment ends with the event that the next tick writes, so a walk of n blocks has n or n + 1 ticks."""
    walk = [0.0, 0.0]
    chop = [0, 0.0]
    trips = []
    by = {}
    for e in events:
        by.setdefault(e["villager"], []).append(e)
    for es in by.values():
        for a, b in zip(es, es[1:]):
            if a["event"] in ("walk", "carry") and b["walked"] > a["walked"]:
                walk[0] += b["walked"] - a["walked"]
                walk[1] += b["t"] - a["t"]
            if a["event"] == "chop" and b["event"] == "carry":
                chop[0] += b["load"] - a["load"]
                chop[1] += b["t"] - a["t"]
        drops = [e for e in es if e["event"] == "drop"]
        trips += [(b["t"] - a["t"], b["walked"] - a["walked"]) for a, b in zip(drops, drops[1:])]
    return {"walk": walk[0] / walk[1] if walk[1] else None, "chop": chop[0] / chop[1] if chop[1] else None,
            "trip": sum(t for t, _ in trips) / len(trips) if trips else None,
            "trip_blocks": sum(w for _, w in trips) / len(trips) if trips else None}


def configured(tick, chop, carry, trip_blocks):
    """The values that the settings of Gather give (straight steps). A trip has 2 ticks for state changes."""
    return {"walk": 1 / tick, "chop": 1 / chop, "trip": trip_blocks * tick + carry * chop + 2 * tick}


def aoe2(T, trip_blocks, speed=1.0):
    """AoE2 values in blocks at tile size T, per game second (speed 1) or at Normal speed (1.7)."""
    walk, work = AOE2_SPEED * T * speed, AOE2_WORK * speed
    return {"walk": walk, "chop": work, "trip": trip_blocks / walk + AOE2_CARRY / work}


def table(m, conf, T):
    b = m["trip_blocks"] or 0
    rows = [("Walk (blocks/s)", "walk"), ("Chop (wood/s)", "chop"), (f"One trip of {b:.0f} blocks (s)", "trip")]
    a1, a17 = aoe2(T, b), aoe2(T, b, NORMAL)
    out = ["| | measured | configured | AoE2, per game second | AoE2 at Normal speed (1.7x) |", "|---|---|---|---|---|"]
    for label, k in rows:
        v = m[k]
        out.append(f"| {label} | {'-' if v is None else f'{v:.2f}'} | {conf[k]:.2f} | {a1[k]:.2f} | {a17[k]:.2f} |")
    return "\n".join(out)


def measure(distance=10, loads=2, tick=0.25, chop=1.0, carry=10, log=None, version=None, timeout=300):
    """Convert the measure map, play on a server until loads loads are dropped. Returns (events, tile size)."""
    import time

    import aoe2mc
    import gather
    import mc_check
    import run
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        src = scenario(os.path.join(tmp, "measure.aoe2scenario"), distance)
        world = os.path.join(tmp, "MeasureWorld")
        with contextlib.redirect_stdout(io.StringIO()):
            aoe2mc.convert(src, world)
        with open(os.path.join(world, "aoe2mc.json")) as f:
            data = json.load(f)
        buf = io.StringIO()
        with run.Game(world, version or mc_check.DEFAULT_VERSION) as game:
            game.forceload()
            end = time.time() + 60                                 # entities load in other threads
            while True:
                g = gather.Gather(game, data, tick=tick, carry=carry, chop=chop, log=buf).setup()
                if g.villagers:
                    break
                if time.time() > end:
                    raise RuntimeError("the villager did not load")
                time.sleep(1)
            uuid, = g.villagers
            tree, = g.map.trees
            g.select(uuid)
            g.send(tree)
            g.run(timeout, until=lambda: g.wood >= loads * carry)
        if log:
            with open(log, "w") as f:
                f.write(buf.getvalue())
        return [json.loads(line) for line in buf.getvalue().splitlines()], data["tile_size"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--distance", type=int, default=10, help="tiles from the town center to the tree (default 10)")
    ap.add_argument("--loads", type=int, default=2, help="loads to drop before the end (default 2)")
    ap.add_argument("--log", metavar="FILE", help="write the event log (JSON lines)")
    ap.add_argument("--read", metavar="FILE", help="only read the event log of game/run.py --play --log FILE")
    ap.add_argument("--version", help="Minecraft version of the server")
    ap.add_argument("--tile-size", type=int, default=4, help="--read: tile size of the world (default 4)")
    a = ap.parse_args(argv)
    tick, chop, carry = 0.25, 1.0, 10                              # the defaults of gather.Gather
    if a.read:
        with open(a.read) as f:
            events, T = [json.loads(line) for line in f if line.strip()], a.tile_size
    else:
        events, T = measure(a.distance, a.loads, tick, chop, carry, a.log, a.version)
    m = analyze(events)
    print(table(m, configured(tick, chop, carry, m["trip_blocks"] or 0), T))


if __name__ == "__main__":
    main()
