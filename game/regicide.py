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
A new King comes with the other start items of the mode (#2388): the units of "more" (7 villagers) and a construction
site of each building of "sites" (the Castle, free) next to the town center. "start" holds the starting resources
of each level of run.py --resources, and "swap" the technologies that the mode puts in place of others (train.unlocked:
Treason for Spies). Treason lets the enemy Kings glow (reveal).
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


def setup(g, mode="regicide", start=True):
    """Give each player (not Gaia) its Kings: tag the ones of the scenario, else summon the start units of the mode in
    front of its first town center, with the more units and buildings of the mode, and the starting resources of the
    mode for the level of aoe2mc.json "resources" (run.py; start False: a loaded game keeps its stock). g.kings: the
    players that have a King, the players of the mode."""
    import gather                                                      # gather imports this module
    import train                                                       # train imports gather, gather imports this module
    level = start and "resources" in g.data and gather.level(g.data["resources"], g.data)
    gathers = {x.player: x for x in [g, *(s.g for s in g.bots)]}       # an own unit goes to the Gather of its player
    for x in gathers.values():
        start_stock(x, MODES[mode], level)
    g.kings = set()
    lost = vars(g).get("defeated", set())                              # a loaded game: its King died before the save
    for n in sorted(int(p) for p in g.players if int(p) and int(p) not in lost):
        for o in g.data["objects"]:
            if o["kind"] == "unit" and o["player"] == n and o["name"] in MODES[mode]["units"] and "uuid" in o:
                g.command(f"tag {o['uuid']} add {KING}")
        if not has_king(g, n):
            tc = next((o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == n
                       and o["name"] == "TOWN_CENTER" and "footprint" in o), None)
            cells = tc and g.map.front((tc[0], tc[2], tc[1], tc[3]))  # footprint (x0, z0, x1, z1) -> rect
            more = [u for u, c in MODES[mode].get("more", {}).items() for _ in range(c)]
            for k, name in enumerate([*MODES[mode]["units"], *more] if cells else ()):
                x, z = cells[k % len(cells)]
                uuid = train.summon(gathers.get(n, g), name, (x + 0.5, float(g.map.y(x, z)), z + 0.5), player=n)
                if uuid and k < len(MODES[mode]["units"]):
                    g.command(f"tag {uuid} add {KING}")
            if tc and n in gathers:
                for name, count in sorted(MODES[mode].get("sites", {}).items()):
                    for _ in range(count):
                        found(gathers[n], name, ((tc[0] + tc[2]) // 2, (tc[1] + tc[3]) // 2))
        if has_king(g, n):
            g.kings.add(n)
    return g


def start_stock(x, line, level):
    """The starting resources of the mode (its key "start") in place of those of level for the Gather x: the
    civilization bonuses stay (#2388)."""
    import gather                                                      # gather imports this module
    for r, v in line.get("start", {}).get(level, {}).items():
        x.stock[r] = max(0, x.stock[r] + v - gather.LEVELS[level][r])
        x.command(f"scoreboard players set {r.capitalize()} {x.board} {x.stock[r]}")


def found(x, name, cell):
    """A free construction site of building name of the Gather x next to the block cell (the town center), if there
    is room."""
    import build                                                       # build imports gather, gather imports this module
    rect = build.near(x, name, cell)
    if rect is None:
        return
    price = build.price(x, name)
    build.found(x, name, rect)
    for r, v in price.items():                                         # build.found pays: give it back
        x.stock[r] += v
        x.command(f"scoreboard players add {r.capitalize()} {x.board} {v}")


def reveal(g, seconds):
    """Treason (#2388): the Kings of the enemies of the player of g glow for `seconds` AoE2 seconds. The Minecraft
    effect Glowing shows a mob through the blocks."""
    import gather                                                      # gather imports this module
    real = max(1, round(seconds / getattr(g, "speed", 1.0)))
    for n in sorted(int(p) for p in g.players if int(p) and not gather.allied(g.players, g.player, int(p))):
        g.command(f"effect give @e[tag=aoe2mc.p{n},tag={KING}] minecraft:glowing {real} 0 true")


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
        conquest.scored(g, n)                                          # a "Player Defeated" trigger (#2710)
        if n == g.player:
            return cheats.end("Defeat", "red")(g, None)
        cheats.destroy(g, n)
        g.command("tellraw @a " + json.dumps({"text": f"The King of player {n} died: player {n} is defeated.",
                                              "color": "red"}))
        g.conquest_at = 0.0                                            # conquest.tick: the "Victory" check now
