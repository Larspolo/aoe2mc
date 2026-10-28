"""
The scenario mode of the game program (#2540, epic #2538; run.py --mode scenario): each player starts with the start
resources and the population limit of the scenario (tab "Players" of the AoE2 DE scenario editor), not with the lobby
settings. The converter writes them into aoe2mc.json "players" ("resources", "pop_limit", #2539). A player without
them (a random map, a recorded game, an old scenario) keeps the lobby values.

A scenario trigger with the effect "Declare Victory" ends the game (#2542): its datapack function sets the score
#p<N> of aoe_win to 1 (aoe2mc.trigger_files), and tick() reads it with RCON once per conquest.EVERY seconds. Player N
and its allies see "Victory", the others "Defeat" (cheats.over). Minecraft feature: a scoreboard, no own logic in the
world.

    scenario.tick(g)    # gather.Gather.run, in the scenario mode
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402
import train  # noqa: E402


def bot_seats(players, people):
    """[(player, foe)] of the bots of the scenario mode (#2543): one bot for each computer player of aoe2mc.json
    "players" after the seats of the people. Its foe is the first human player of the scenario that is not its ally
    (gather.allied), else player 1, as run.bot_seat. A human seat that no person takes stays idle, as in AoE2."""
    computer = sorted(int(p) for p, row in players.items() if row.get("computer") and int(p) > people)
    humans = sorted(int(p) for p, row in players.items() if not row.get("computer") and int(p) > 0)
    return [(b, next((p for p in humans if not gather.allied(players, b, p)), 1)) for b in computer]


def setup(g, mode="scenario"):
    """Put the scenario start values on the Gather of each player (the people and the bots) and show them."""
    sides = [g, *(s.g for s in g.bots)]
    rows = {x: g.players.get(str(x.player), {}) for x in sides}
    if not any("resources" in p or "pop_limit" in p for p in rows.values()):
        print("The world has no scenario start values: the game starts with the lobby settings.", file=sys.stderr)
        return g
    for x, p in rows.items():
        x.stock.update(p.get("resources", {}))
        x.pop_limit = p.get("pop_limit", x.pop_limit)
        for r in gather.RESOURCES:                                     # the sidebar of the resources (Gather.setup)
            x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
        train.sidebar(x)
    return g


def tick(g):
    """End the game when a trigger declared the victory of a player (the score #p<N> of aoe_win is 1)."""
    import cheats, conquest                                            # they import gather: import them late
    if g.ended or g.clock() < vars(g).get("win_at", 0.0):
        return
    g.win_at = g.clock() + conquest.EVERY
    for n in sorted(int(p) for p in g.players if int(p)):
        got = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #p{n} aoe_win") or "")
        if got and int(got[1]) > 0:
            return cheats.over(g, lambda m: gather.allied(g.players, n, m))   # allies win together
