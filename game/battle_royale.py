"""
The Corruption of the AoE2 DE game mode "Battle Royale" in the game program (#2439, epic #2263; run.py --mode
battle-royale): it takes the map from its border to its center in MINUTES game minutes and destroys each unit and
building that it touches (AoE2 wiki "Battle Royale"; its recommended Time is 30 minutes).
Minecraft feature: the world border shows the Corruption (the red wall and the red screen edge). It hurts only players
(Paper 26.3, #2439: a zombie and a slime outside it keep their health), and the players play in creative mode, so
tick() destroys the units and buildings outside it: four volume selectors around the border square, "aoe destroy" for a
building (it falls as at 0 hit points) and kill for the other entities of a team (units, their mounts).
gather.Gather.run gives tick() the game seconds; the border moves each EVERY game seconds, so a paused game stops it.
The start (#2686): the line "battle-royale" of game/data/setup.jsonl gives the Post-Imperial Age ("age"), the High
resources ("level") and no stone ("none"); setup() removes the town centers and the villagers of each player, as
"Town Centers and Villagers are not part of the game mode" (AoE2 wiki). A loaded game does not call setup() (its
"loaded" is "skip"): the world keeps its border, the save its Corruption time and its stock.
The two heroes (#2688): heroes() gives each player (not Gaia) the units of the key "heroes" (Attila the Hun and Alaric
the Goth, AoE2 wiki "BR Fall of Rome") next to its first town center, else next to its first unit. A hero of the
scenario counts: no second one. A spawned hero gets the key "hero" in g.data["objects"] (a monk cannot convert it,
monk.convertible) and regenerates (the key "regen" of data/units.jsonl, regen.heroes).
The rest of the mode (the camps and Guardians to capture) is not here.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

MINUTES = 30            # game minutes until the Corruption reaches the center (AoE2 wiki, the recommended "Time")
EVERY = 3.0             # game seconds between two steps of the border
FAR = 30000             # blocks: the strips outside the border reach this far
MODE = next(r for r in table.load("setup.jsonl") if r["name"] == "battle-royale")


def side(g):
    """The side of the map square in blocks."""
    return (g.data.get("map_size") or g.map.n / g.map.T) * g.map.T


def width(g):
    """The width of the border after the game seconds g.corruption_time: the map side at the start, 0 at the end."""
    return max(0.0, side(g) * (1 - vars(g).get("corruption_time", 0.0) / (MINUTES * 60)))


def strips(c, w):
    """The four volume selector parts (x, y, z, dx, dy, dz) outside the border square of center (c, c) and width w."""
    lo, hi, n = c - w / 2, c + w / 2, 2 * FAR + w
    box = "x={:.1f},y=-64,z={:.1f},dx={:.1f},dy=448,dz={:.1f}"
    return [box.format(lo - FAR, lo - FAR, FAR - 1, n), box.format(hi, lo - FAR, FAR, n),     # west, east
            box.format(lo, lo - FAR, w, FAR - 1), box.format(lo, hi, w, FAR)]                 # north, south


def setup(g, mode="battle-royale"):
    """Remove the town centers and the villagers (start()), give the heroes (heroes()), put the world border on the map
    square and say how long the Corruption takes."""
    start(g)
    heroes(g)
    s = side(g)
    g.corruption_time, g.corruption_at = 0.0, 0.0
    for c in (f"worldborder center {s / 2:.1f} {s / 2:.1f}", "worldborder damage buffer 0", f"worldborder set {s:.1f}"):
        g.command(c)
    g.command("tellraw @a " + json.dumps({"text": f"Battle Royale: the Corruption takes the map from its border to its "
                                                  f"center in {MINUTES}:00. It destroys all units and buildings in it.",
                                          "color": "dark_red"}))
    return g


def start(g):
    """The start of the mode: each player (not Gaia) loses its town centers ("aoe destroy" of their targets, Gather.free
    frees the footprints: no razing and no loot, #3113) and its villagers (kill, also the units of a player with no Gather), and each Gather of a
    player has 0 of the resources of the key "none" (stone), but an infinite level keeps them (gather.Endless)."""
    import combat, gather, owners                                      # combat imports gather, gather imports the modes
    objs = [o for o in g.data["objects"] if o["player"] and o["player"] > 0]
    gone = {combat.target_uuid(o["footprint"]) for o in objs
            if o["kind"] == "building" and o["name"] == "TOWN_CENTER" and "footprint" in o}
    dead = {o["uuid"] for o in objs if o["kind"] == "unit" and o["name"].startswith("VILLAGER") and "uuid" in o}
    for u in sorted(gone):
        g.command(f"aoe destroy {u}")
    for u in sorted(dead):
        g.command(f"kill {u}")
    owners.killed(g, dead)                                             # update_enemies keeps them out (#2996)
    for u in sorted(gone):                                             # no razing and no loot: not Gather.fall (#3113)
        g.free(u)
    for x in [g, *(b.g for b in getattr(g, "bots", ()))]:
        x.villagers = {u: v for u, v in x.villagers.items() if u not in dead}
        x.units = [o for o in x.units if o.get("uuid") not in dead]
        x.enemies = {u: k for u, k in x.enemies.items() if u not in dead}
        if isinstance(x.stock, gather.Endless):
            continue
        for r in MODE.get("none", ()):
            x.stock[r] = 0
            x.command(f"scoreboard players set {r.title()} {x.board} 0")   # the sidebar (Gather.setup)


def heroes(g):
    """Summon the units of the key "heroes" for each player (not Gaia) that has none of them yet, on the spawn cells of
    its first town center (the footprint stays in g.data after start()), else next to its first unit (its "tile")."""
    import train                                                       # train imports gather, gather imports the modes
    if not (players := sorted(int(p) for p in getattr(g, "players", {}) if int(p))):
        return
    gathers = {x.player: x for x in [g, *(b.g for b in getattr(g, "bots", ()))]}   # an own unit to its own Gather
    objs = g.data["objects"]
    for n in players:
        own = [o for o in objs if o["player"] == n]
        has = {o["name"] for o in own if o["kind"] == "unit"}
        tc = next((o["footprint"] for o in own if o["kind"] == "building" and o["name"] == "TOWN_CENTER"
                   and "footprint" in o), None)
        tile = next((o["tile"] for o in own if o["kind"] == "unit" and "tile" in o), None)
        x, z = tile and (math.floor(tile[0] * g.map.T), math.floor(tile[1] * g.map.T)) or (0, 0)
        rect = (tc[0], tc[2], tc[1], tc[3]) if tc else tile and (x, x + 1, z, z + 1)   # footprint (x0, z0, x1, z1)
        cells = rect and g.map.front(rect, mounted=True)
        for k, name in enumerate([h for h in MODE["heroes"] if h not in has] if cells else ()):
            x, z = cells[k % len(cells)]
            if uuid := train.summon(gathers.get(n, g), name, (x + 0.5, float(g.map.y(x, z)), z + 0.5), player=n):
                objs.append(dict(kind="unit", name=name, player=n, uuid=uuid, hero=True, tile=[x / g.map.T, z / g.map.T]))


def tick(g, dt):
    """Move the border after dt game seconds, each EVERY seconds, and destroy what is outside it."""
    if g.ended:
        return
    g.corruption_time = vars(g).get("corruption_time", 0.0) + dt
    if g.corruption_time < vars(g).get("corruption_at", 0.0):
        return
    g.corruption_at = g.corruption_time + EVERY
    w = width(g)
    g.command(f"worldborder set {max(w, 1.0):.1f}")                   # the smallest width that Minecraft takes
    for sel in strips(side(g) / 2, w):
        g.command(f"aoe destroy @e[tag=aoe2mc.building,{sel}]")
        g.command(f"kill @e[team=!,type=!player,{sel}]")              # team=!: on any team, the units and their mounts
