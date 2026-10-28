"""
The AoE2 DE game mode "Sudden Death" in the game program (#2407, epic #2263; run.py --mode sudden-death): each player
can have only one town center, and a player who loses it is defeated (AoE2 wiki "Sudden Death"). The build menu
refuses a second town center in this mode (build.locked).
A town center is one of aoe2mc.json or a construction site of the player whose target entity stands (build.town_center).
A player with no town center at the start (a Nomad map) is not in the mode until it has one: only the conquest rule
(conquest.py) can defeat it before. gather.Gather.run calls tick() each conquest.EVERY seconds. A defeated player goes
into the sets of conquest.py (g.defeated, g.conquest_seen), so conquest.tick gives the "Victory" when only allies are
left, as regicide.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import conquest  # noqa: E402


def has_town_center(g, n):
    """Player n has a town center: build.town_center with the Gather of player n (its construction sites)."""
    x = {x.player: x for x in [g, *(s.g for s in g.bots)]}.get(n, g)
    return build.town_center(x, n)


def setup(g, mode="sudden-death"):
    """g.towns: the players (not Gaia) that have a town center, the players of the mode."""
    g.towns = {n for n in sorted(int(p) for p in g.players if int(p)) if has_town_center(g, n)}
    return g


def tick(g):
    """Check the town centers each conquest.EVERY seconds: defeat each player who lost its town center."""
    if g.ended or g.clock() < vars(g).get("sudden_death_at", 0.0):
        return
    g.sudden_death_at = g.clock() + conquest.EVERY
    seen, lost = vars(g).setdefault("conquest_seen", set()), vars(g).setdefault("defeated", set())
    towns = vars(g).setdefault("towns", set())
    for n in sorted(int(p) for p in g.players if int(p) and int(p) not in lost):
        if has_town_center(g, n):
            towns.add(n)                                               # also a first town center of a Nomad map
            continue
        if n not in towns:
            continue
        seen.add(n)
        conquest.defeat(g, n, f"The town center of player {n} fell: player {n} is defeated.")   # also conquest.scored, the end (#3103)
        if g.ended:
            return
