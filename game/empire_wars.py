"""
The AoE2 DE game mode "Empire Wars" in the game program (#2408, epic #2263; run.py --play --mode empire-wars): each
player starts in the Feudal Age with a small town and villagers that already work (AoE2 wiki "Empire Wars"). The line
"empire-wars" of game/data/setup.jsonl holds the start: the key "age" (a start age of train.STARTS, as --age, #2265),
"buildings" (name: count) and "villagers" (resource: count).
The buildings come complete and free (build.found, build.rise) on free ground: a drop site next to the nearest source of
its resource (the key "near" of game/data/build.jsonl, as the bot builds), the farms next to the mill, the others next
to the town center. New villagers stand in front of the town center (train.spawn) until the player has the count of the
mode, and each villager gets a gather order (Gather.send): the path finding of Minecraft walks it there. A villager
whose resource has no free source (no fruit bush, all farms taken) chops wood.
Only the players with a Gather (the people and the bot) get the town: the other players of a scenario do not play.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import table  # noqa: E402

MODES = {r["name"]: r for r in table.load("setup.jsonl") if "buildings" in r}
NEAR = {r["name"]: r["near"] for r in build.ROWS if "near" in r}


def middle(rect):
    x0, x1, z0, z1 = rect
    return (x0 + x1) // 2, (z0 + z1) // 2


def sources(g, res):
    """{tile: amount} of the trees, the mines of res, or the fruit bushes and the own farms without a farmer."""
    m = g.map
    if res == "food":
        return {**m.bushes, **{t: k for t, k in m.farms.items() if t in m.own_farms and t not in g.farmers}}
    return m.trees if res == "wood" else m.mines[res]


def nearest(g, res, cell, n=1):
    """The n source tiles of res with something left and a free cell next to them (not inside a forest) that are
    nearest to the block cell, the nearest first; the free own farms before the bushes (wiki: 2 farmers, 4 foragers)."""
    T = g.map.T
    full = [t for t, k in sources(g, res).items() if k > 0 and g.goals(t)]
    return sorted(full, key=lambda t: (t not in g.map.farms, math.dist(cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), t))[:n]


def town(g, mode, tc):
    """Put the complete buildings of the mode next to the town center rect tc. Returns the sites."""
    out = []
    for name, count in sorted(MODES[mode]["buildings"].items(), key=lambda b: (b[0] not in NEAR, b[0] == "FARM", b[0])):
        for _ in range(count):
            center = middle(tc)
            if (res := NEAR.get(name)) and (tiles := nearest(g, res, center)):
                center = tiles[0][0] * g.map.T + g.map.T // 2, tiles[0][1] * g.map.T + g.map.T // 2
            elif name == "FARM" and (mill := next((s for s in out if s["name"] == "MILL"), None)):
                center = middle(mill["footprint"])
            if (rect := build.near(g, name, center)) is None:
                continue
            site = build.found(g, name, rect, free=True)
            build.rise(g, site, math.inf)                              # complete at once
            out.append(site)
    return out


def setup(g, mode="empire-wars"):
    """Give each player with a Gather its town and its villagers at work. g: the Gather of player 1."""
    import train  # train imports gather, gather imports build
    for x in [g, *(s.g for s in getattr(g, "bots", ()))]:
        tc = next((r for r, n in sorted(train.homes(x).items()) if n == "TOWN_CENTER"), None)
        if tc is None:
            continue
        town(x, mode, tc)
        jobs = MODES[mode]["villagers"]
        while len(x.villagers) < sum(jobs.values()) and train.spawn(x, tc, "VILLAGER_MALE"):
            x.pop += 1
        idle = sorted(x.villagers)
        for res, count in sorted(jobs.items()):
            tiles = nearest(x, res, middle(tc), count)
            for i, u in enumerate(idle[:count]):                       # a farm takes one farmer: look again
                cell = x.villagers[u].cell
                to = nearest(x, res, cell) if res == "food" else tiles[i % max(len(tiles), 1):][:1]
                if to := to or nearest(x, "wood", cell):               # no source of res left: wood, not idle
                    x.send(to[0], {u})
            idle = idle[count:]
        train.census(x)
        x.idle()
    return g
