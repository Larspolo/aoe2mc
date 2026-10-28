"""
The sidebar of the spectators (#2900, epic #2897), as the AoE2 DE spectator overlay: the resources and the population
of each player. A Minecraft player without a side is on the team spec (run.SPECTATORS, color gray, #2898), so the
objective aoe_spec goes into the display slot of that team color (Minecraft feature: one sidebar per team color). Each
player has the lines "P<N> Food", "P<N> Wood", "P<N> Gold", "P<N> Stone" and "P<N> Pop" (a holder name has no space:
the holder is p<N>_<name>, its display name has the space). The sidebar shows at most 15 lines: three players fit.
The sidebar of each player (Gather.board, Gather.sidebars) does not change. A player with the color gray (player 7)
keeps its own sidebar: then the spectators see none.

    spectator.tick(g)    # gather.Gather.run, once each second; fog.gathers(g): the person, its bots and the other persons
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fog  # noqa: E402

BOARD = "aoe_spec"
SLOT = "sidebar.team.gray"                                             # the color of the team spec (run.SPECTATORS)
EVERY = 1.0                                                            # seconds between two updates
NAMES = ("Food", "Wood", "Gold", "Stone")                              # the AoE2 order of the resource panel


def lines(x):
    """The lines of the Gather x: {holder: (display name, value)}."""
    out = {f"p{x.player}_{r.lower()}": (f"P{x.player} {r}", x.stock[r.lower()]) for r in NAMES}
    out[f"p{x.player}_pop"] = (f"P{x.player} Pop", x.pop)
    return out


def tick(g):
    """Once each EVERY seconds: set each line of each Gather of the game that changed, one command per change. The
    first call makes the objective and shows it to the spectators."""
    if not hasattr(g, "clock") or g.clock() < vars(g).get("spectator_at", 0.0):   # a test loop with no clock
        return
    g.spectator_at = g.clock() + EVERY
    sides = fog.gathers(g)
    sent = vars(g).get("spectator_sent")
    if sent is None:
        g.spectator_sent = sent = {}
        g.command(f'scoreboard objectives add {BOARD} dummy "Players"')
        if all(x.color() != "gray" for x in sides):
            g.command(f"scoreboard objectives setdisplay {SLOT} {BOARD}")
    for x in sides:
        for holder, (name, n) in lines(x).items():
            if sent.get(holder) != n:
                if holder not in sent:
                    g.command(f"scoreboard players display name {holder} {BOARD} {json.dumps(name)}")
                g.command(f"scoreboard players set {holder} {BOARD} {n}")
                sent[holder] = n
