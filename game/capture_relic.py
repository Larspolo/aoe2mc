"""
The AoE2 DE game mode "Capture the Relic" in the game program (#2440, epic #2263; run.py --mode capture-the-relic):
one relic lies at the center of the map, and the first player whose monk carries it into an own monastery wins at
once (AoE2 wiki "Capture the Relic": "the first team's Monk to pick it up and take it to their Monastery immediately
wins"). Its allies win with it, and the rivals see "Defeat" (cheats.over).
The relic is one of monk.relics with the key "center": the pot block of the converter's relics (monk.POT) and the same
monk orders (monk.order, monk.relic_tick). Each Gather (the human player, each bot) holds its own list of the relics,
so setup() adds the center relic to each list and places one pot. A loaded game (savegame) has the relic in its saved
lists and its world: run.play calls setup() only for a new game.
gather.Gather.run calls tick() at each step. The relics of the scenario stay, but only the center relic wins.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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


def setup(g, mode="capture-the-relic"):
    """Put the relic at the map center: a pot block, and an entry with "center" in the relics of each Gather."""
    x, z = center(g)
    for h in fog.gathers(g):
        if not any(r.get("center") for r in monk.relics(h)):         # a list that two Gathers share: one relic
            monk.relics(h).append({"at": (x, z), "monk": None, "home": None, "center": True})
    g.command(f"setblock {x} {g.map.y(x, z)} {z} {monk.POT} keep")
    return g


def tick(g):
    """End the game when the center relic is in a monastery of its holder: its player and allies win."""
    if g.ended:
        return
    for h in fog.gathers(g):
        if any(r.get("center") and r["home"] in monk.monasteries(h) for r in monk.relics(h)):
            from gather import allied                                  # gather imports this module
            return cheats.over(g, lambda n: allied(g.players, h.player, n))
