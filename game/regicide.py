"""
The AoE2 DE game mode "Regicide" in the game program (#2347, epic #2263; run.py --mode regicide): each player starts
with a King, and a player whose Kings all died is defeated (AoE2 wiki "Regicide (game mode)"). The start units of a
mode are the key "units" of its line in game/data/setup.jsonl.
A King is a unit of its player as the others (units.make_entity), with the entity tag KING: the King of the scenario
gets it at the start, and a player with no King gets a new one in front of its first town center (train.summon). The
tag stays in the world, so a loaded game (savegame) finds its Kings again and gives no second King. A player with no
King and no town center is not in the mode: only the conquest rule (conquest.py) can defeat it.
gather.Gather.run calls tick() each conquest.EVERY seconds. A defeated player goes into the sets of conquest.py
(g.defeated, g.conquest_seen), so conquest.tick gives the "Victory" when only allies are left.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cheats  # noqa: E402
import conquest  # noqa: E402
import table  # noqa: E402

MODES = {r["name"]: r for r in table.load("setup.jsonl") if "units" in r}   # the modes other than "standard"
KING = "aoe2mc.king"                                                         # the entity tag of a King


def has_king(g, n):
    """Player n has a King that lives."""
    return "passed" in g.command(f"execute if entity @e[tag=aoe2mc.p{n},tag={KING}]")


def setup(g, mode="regicide"):
    """Give each player (not Gaia) its Kings: tag the ones of the scenario, else summon the start units of the mode in
    front of its first town center. g.kings: the players that have a King, the players of the mode."""
    import train                                                       # train imports gather, gather imports this module
    gathers = {x.player: x for x in [g, *(s.g for s in g.bots)]}       # an own unit goes to the Gather of its player
    g.kings = set()
    for n in sorted(int(p) for p in g.players if int(p)):
        for o in g.data["objects"]:
            if o["kind"] == "unit" and o["player"] == n and o["name"] in MODES[mode]["units"] and "uuid" in o:
                g.command(f"tag {o['uuid']} add {KING}")
        if not has_king(g, n):
            tc = next((o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == n
                       and o["name"] == "TOWN_CENTER" and "footprint" in o), None)
            cells = tc and g.map.front((tc[0], tc[2], tc[1], tc[3]))  # footprint (x0, z0, x1, z1) -> rect
            for k, name in enumerate(MODES[mode]["units"] if cells else ()):
                x, z = cells[k % len(cells)]
                uuid = train.summon(gathers.get(n, g), name, (x + 0.5, float(g.map.y(x, z)), z + 0.5), player=n)
                if uuid:
                    g.command(f"tag {uuid} add {KING}")
        if has_king(g, n):
            g.kings.add(n)
    return g


def tick(g):
    """Check the Kings each conquest.EVERY seconds: defeat each player whose Kings all died."""
    if g.ended or g.clock() < vars(g).get("regicide_at", 0.0):
        return
    g.regicide_at = g.clock() + conquest.EVERY
    seen, lost = vars(g).setdefault("conquest_seen", set()), vars(g).setdefault("defeated", set())
    for n in sorted(vars(g).get("kings", set()) - lost):
        if has_king(g, n):
            continue
        seen.add(n)
        lost.add(n)
        if n == g.player:
            return cheats.end("Defeat", "red")(g, None)
        cheats.destroy(g, n)
        g.command("tellraw @a " + json.dumps({"text": f"The King of player {n} died: player {n} is defeated.",
                                              "color": "red"}))
        g.conquest_at = 0.0                                            # conquest.tick: the "Victory" check now
