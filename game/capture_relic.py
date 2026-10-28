"""
The AoE2 DE game mode "Capture the Relic" in the game program (#2440, epic #2263; run.py --mode capture-the-relic):
one relic lies at the center of the map, and the first player whose monk carries it into an own monastery wins at
once (AoE2 wiki "Capture the Relic": "the first team's Monk to pick it up and take it to their Monastery immediately
wins"). Its allies win with it, and the rivals see "Defeat" (cheats.over).
The relic is one of monk.relics with the key "center": the pot block of the converter's relics (monk.POT) and the same
monk orders (monk.order, monk.relic_tick). All Gathers of a game (the people, each bot) share one list of the relics
(#3116), so setup() adds the center relic once and places one pot. A loaded game (savegame) has the relic in its saved
list and its world: run.play calls setup() only for a new game.
gather.Gather.run calls tick() at each step. The relics of the scenario stay, but only the center relic wins.
Each player with a town center also starts with a complete, free monastery next to it that nothing can destroy, and
cannot build more monasteries (#2458, wiki: "a pre-built, indestructible Monastery, though at the cost of not being able
to build more Monasteries"): its site has "lasting", so build.target gives it no target entity (no mob attacks it, no
hit points to lose), and build.locked refuses a monastery in the mode.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import cheats  # noqa: E402
import fog  # noqa: E402
import monk  # noqa: E402

SEARCH = 8      # tiles from the center: a free block cell for the relic when a building stands at the center


def center(g):
    """The block cell of the relic: the map center, else the nearest free cell with ground (not in a footprint)."""
    m = g.map
    c, r = m.n // 2, SEARCH * m.T
    cells = sorted(((x, z) for x in range(c - r, c + r + 1) for z in range(c - r, c + r + 1)),
                   key=lambda p: (math.dist(p, (c, c)), p))
    return next((p for p in cells if m.free(*p)), (c, c))


def monastery(g):
    """Put the lasting monastery of the player of g next to its first town center (once). Returns its site or None."""
    import train                                                       # train imports gather, gather imports build
    tc = next((r for r, n in sorted(train.homes(g).items()) if n == "TOWN_CENTER"), None)
    if tc is None or any(s.get("lasting") for s in g.sites):
        return None
    x0, x1, z0, z1 = tc
    if (rect := build.near(g, "MONASTERY", ((x0 + x1) // 2, (z0 + z1) // 2))) is None:
        return None
    site = build.found(g, "MONASTERY", rect, free=True)
    site["lasting"] = True                                             # before rise: build.target skips it
    build.rise(g, site, math.inf)                                      # complete at once
    return site


def setup(g, mode="capture-the-relic"):
    """Put the relic at the map center: a pot block, and an entry with "center" in the shared relic list. Give
    each player with a town center its lasting monastery."""
    x, z = center(g)
    for h in fog.gathers(g):
        if not any(r.get("center") for r in monk.relics(h)):         # a list that two Gathers share: one relic
            monk.relics(h).append({"at": (x, z), "monk": None, "home": None, "center": True})
    g.command(f"setblock {x} {g.map.y(x, z)} {z} {monk.POT} keep")
    for h in {id(h): h for h in [g, *(b.g for b in getattr(g, "bots", ()))]}.values():
        monastery(h)
    return g


def tick(g):
    """End the game when the center relic is in a monastery of its holder: its player and allies win."""
    if g.ended:
        return
    for h in fog.gathers(g):
        if any(r.get("center") and r["home"] in monk.monasteries(h) for r in monk.relics(h)):
            from gather import allied                                  # gather imports this module
            return cheats.over(g, lambda n: allied(g.players, h.player, n))
