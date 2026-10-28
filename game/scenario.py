"""
The scenario mode of the game program (#2540, epic #2538; run.py --mode scenario): each player starts with the start
resources and the population limit of the scenario (tab "Players" of the AoE2 DE scenario editor), not with the lobby
settings. The converter writes them into aoe2mc.json "players" ("resources", "pop_limit", #2539). A player without
them (a random map, a recorded game, an old scenario) keeps the lobby values. tick: the trigger effects "Tribute" and
"Modify Resource" change the stocks (#2576).
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402
import train  # noqa: E402


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


EVERY = 1.0                                                            # seconds between two reads of the scores


def tick(g):
    """The trigger effects "Tribute" and "Modify Resource" of the converted world (#2576, aoe2mc.resource_lines): read
    the scores #p<N>.<resource> of aoe_set (a new value) and aoe_res (a change) with RCON once per EVERY seconds, put
    them into the stock of the Gather of player N, and reset them. A stock does not go below 0."""
    if time.time() < vars(g).get("scenario_at", 0.0):
        return
    g.scenario_at = time.time() + EVERY
    for x in [g, *(s.g for s in g.bots)]:
        for r in gather.RESOURCES:
            changed, name = False, f"#p{x.player}.{r.lower()}"
            for obj in ("aoe_set", "aoe_res"):
                if m := re.search(r" has (-?\d+) ", g.command(f"scoreboard players get {name} {obj}") or ""):
                    x.stock[r.lower()] = max(int(m[1]) + (x.stock[r.lower()] if obj == "aoe_res" else 0), 0)
                    g.command(f"scoreboard players reset {name} {obj}")
                    changed = True
            if changed:
                x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
