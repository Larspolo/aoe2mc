#!/usr/bin/env python3
"""
Measure the gather timing of game/gather.py on a real server and compare it with AoE2 (#289, #393).

Usage:
    python3 tools/measure_gather.py [--resource wood] [--distance 10] [--loads 2] [--log OUT.jsonl] [--version 26.3] [--server vanilla]
    python3 tools/measure_gather.py --read F.jsonl     # only read a log of game/run.py --play --log F.jsonl

The tool makes a flat map with one villager of player 1, a town center and one resource in one row (`--distance`
tiles from the center of the town center): a tree (wood), a fruit bush (food), a farm, a gold mine or a stone mine.
It converts the map, starts a server without a client, sends the villager to the resource (no click) and plays in
real time until the villager dropped `--loads` loads. Then it prints the measured walk speed, work rate and trip
time next to the configured values and AoE2. On Paper (the default) the villager walks with Minecraft path finding
at the AoE2 speed (#437). With `--server vanilla` it walks one block per tick: a row is straight, so no step is
diagonal (a diagonal step is 1.41 blocks in one tick).
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

# AoE2 DE villagers, per game second: speed 0.8 tiles/s, carry 10 (unit 123 VMLUM, owner's data in #267). The work
# rates per resource are in game/gather.py (AOE2_WORK, #393).
import ai  # noqa: E402
from gather import AOE2_WORK, NORMAL, WORK_SECONDS  # noqa: E402

AOE2_SPEED, AOE2_CARRY = 0.8, 10                                   # tiles/s, resource
RESOURCES = {"wood": ("TREE_OAK", "wood"), "food": ("FRUIT_BUSH", "food"), "farm": ("FARM", "food"),
             "gold": ("GOLD_MINE", "gold"), "stone": ("STONE_MINE", "stone")}    # --resource -> object, stock


def scenario(path, distance=10, resource="wood"):
    """A flat grass map: town center at tile (6, 12), the villager next to it, the resource distance tiles east."""
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.players import PlayerId
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(max(24, 6 + distance + 6))
    um = scn.unit_manager
    um.add_unit(PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=6, y=12)
    um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=9.5, y=12.5)
    name = RESOURCES[resource][0]
    if name == "FARM":
        um.add_unit(PlayerId.ONE, BuildingInfo.FARM.ID, x=6 + distance + 0.5, y=12.5)
    else:
        um.add_unit(PlayerId.GAIA, getattr(OtherInfo, name).ID, x=6 + distance + 0.5, y=12.5)
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


def configured(tick, chop, carry, trip_blocks, walk=None):
    """The values that the settings of Gather give (straight steps). A trip has 2 ticks for state changes.
    walk: blocks per second on Paper (the AoE2 speed of game/ai.py, #437); None: one block per tick (vanilla)."""
    walk = walk or 1 / tick
    return {"walk": walk, "chop": 1 / chop, "trip": trip_blocks / walk + carry * chop + 2 * tick}


def aoe2(T, trip_blocks, speed=1.0, resource="wood"):
    """AoE2 values in blocks at tile size T, per game second (speed 1) or at Normal speed (1.7)."""
    walk, work = AOE2_SPEED * T * speed, AOE2_WORK[resource] * speed
    return {"walk": walk, "chop": work, "trip": trip_blocks / walk + AOE2_CARRY / work}


def table(m, conf, T, resource="wood"):
    b = m["trip_blocks"] or 0
    work = {"wood": "Chop (wood/s)", "food": "Forage (food/s)", "farm": "Farm (food/s)", "gold": "Mine (gold/s)",
            "stone": "Mine (stone/s)"}[resource]
    rows = [("Walk (blocks/s)", "walk"), (work, "chop"), (f"One trip of {b:.0f} blocks (s)", "trip")]
    a1, a17 = aoe2(T, b, 1.0, resource), aoe2(T, b, NORMAL, resource)
    out = ["| | measured | configured | AoE2, per game second | AoE2 at Normal speed (1.7x) |", "|---|---|---|---|---|"]
    for label, k in rows:
        v = m[k]
        out.append(f"| {label} | {'-' if v is None else f'{v:.2f}'} | {conf[k]:.2f} | {a1[k]:.2f} | {a17[k]:.2f} |")
    return "\n".join(out)


def measure(distance=10, loads=2, tick=0.25, chop=None, carry=10, log=None, version=None, timeout=300,
            resource="wood", server="paper"):
    """Convert the measure map, play on a server until loads loads are dropped. Returns (events, tile size)."""
    import time

    import gather
    import mc_check
    import run

    import aoe2mc
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        src = scenario(os.path.join(tmp, "measure.aoe2scenario"), distance, resource)
        world = os.path.join(tmp, "MeasureWorld")
        with contextlib.redirect_stdout(io.StringIO()):
            aoe2mc.convert(src, world)
        with open(os.path.join(world, "aoe2mc.json")) as f:
            data = json.load(f)
        buf = io.StringIO()
        with run.Game(world, version or mc_check.DEFAULT_VERSION, server=server) as game:
            game.forceload()
            end = time.time() + 60                                 # entities load in other threads
            while True:
                g = gather.Gather(game, data, tick=tick, carry=carry, chop=chop or WORK_SECONDS[resource], log=buf).setup()
                if g.villagers:
                    break
                if time.time() > end:
                    raise RuntimeError("the villager did not load")
                time.sleep(1)
            uuid, = g.villagers
            stock = RESOURCES[resource][1]
            tile, = g.map.farms if resource == "farm" else g.map.bushes if resource == "food" else \
                g.map.trees if resource == "wood" else g.map.mines[resource]
            g.select(uuid)
            g.send(tile)
            base = g.stock[stock]                                  # the start resources of AoE2 (#973)
            g.run(timeout, until=lambda: g.stock[stock] >= base + loads * carry)
        if log:
            with open(log, "w") as f:
                f.write(buf.getvalue())
        return [json.loads(line) for line in buf.getvalue().splitlines()], data["tile_size"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resource", choices=RESOURCES, default="wood", help="what the villager gathers (default wood)")
    ap.add_argument("--distance", type=int, default=10, help="tiles from the town center to the resource (default 10)")
    ap.add_argument("--loads", type=int, default=2, help="loads to drop before the end (default 2)")
    ap.add_argument("--log", metavar="FILE", help="write the event log (JSON lines)")
    ap.add_argument("--read", metavar="FILE", help="only read the event log of game/run.py --play --log FILE")
    ap.add_argument("--version", help="Minecraft version of the server")
    ap.add_argument("--server", choices=["paper", "vanilla"], default="paper", help="server program (default: Paper)")
    ap.add_argument("--tile-size", type=int, default=4, help="--read: tile size of the world (default 4)")
    a = ap.parse_args(argv)
    tick, chop, carry = 0.25, WORK_SECONDS[a.resource], 10         # the defaults of gather.Gather
    if a.read:
        with open(a.read) as f:
            events, T = [json.loads(line) for line in f if line.strip()], a.tile_size
    else:
        events, T = measure(a.distance, a.loads, tick, chop, carry, a.log, a.version, resource=a.resource,
                            server=a.server)
    m = analyze(events)
    walk = ai.walk_speed("VILLAGER", T) if a.server == "paper" else None
    print(table(m, configured(tick, chop, carry, m["trip_blocks"] or 0, walk), T, a.resource))


if __name__ == "__main__":
    main()
