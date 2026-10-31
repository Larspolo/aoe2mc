"""
The start buildings of a civilization in the game program (#2429, epic #1088; AoE2 DE wiki "Georgians": "Start with a
Mule Cart. Mule Carts replace Lumber Camps and Mining Camps."). The key "start_buildings" of the line of a civilization
in game/data/civs.jsonl holds them ({building: count}); the camps that a civilization does not have name it in
their key "not_civs" (game/data/build.jsonl, #3200). run.play puts the buildings complete and free next to the own town center at the start of a new game,
as empire_wars.town does (build.found, build.rise). A loaded game has them in the world already.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import civs  # noqa: E402
import empire_wars  # noqa: E402


def used(data):
    """True when a player of aoe2mc.json data has a civilization with start buildings."""
    return any(civs.value("start_buildings", p.get("civ")) for p in dict(data.get("players") or {}).values())


def place(g):
    """Put the start buildings of the civilization of g next to its town center. Returns the sites."""
    import train  # train imports gather, gather imports build
    tc = next((r for r, n in sorted(train.homes(g).items()) if n == "TOWN_CENTER"), None)
    out = []
    for name, count in sorted(civs.value("start_buildings", civs.civ(g), {}).items()) if tc else ():
        for _ in range(count):
            if (rect := build.near(g, name, empire_wars.middle(tc))) is not None:
                site = build.found(g, name, rect, free=True)
                build.rise(g, site, math.inf)                          # complete at once
                out.append(site)
    return out
