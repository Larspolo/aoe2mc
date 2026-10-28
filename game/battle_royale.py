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
The rest of the mode (the two heroes, the camps and Guardians to capture) is not here.
"""
import json
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
    """Remove the town centers and the villagers (start()), put the world border on the map square and say how long
    the Corruption takes."""
    start(g)
    s = side(g)
    g.corruption_time, g.corruption_at = 0.0, 0.0
    for c in (f"worldborder center {s / 2:.1f} {s / 2:.1f}", "worldborder damage buffer 0", f"worldborder set {s:.1f}"):
        g.command(c)
    g.command("tellraw @a " + json.dumps({"text": f"Battle Royale: the Corruption takes the map from its border to its "
                                                  f"center in {MINUTES}:00. It destroys all units and buildings in it.",
                                          "color": "dark_red"}))
    return g


def start(g):
    """The start of the mode: each player (not Gaia) loses its town centers ("aoe destroy" of their targets: Gather.fall
    frees the footprints) and its villagers (kill, also the units of a player with no Gather), and each Gather of a
    player has 0 of the resources of the key "none" (stone), but an infinite level keeps them (gather.Endless)."""
    import combat, gather                                              # combat imports gather, gather imports the modes
    objs = [o for o in g.data["objects"] if o["player"] and o["player"] > 0]
    gone = {combat.target_uuid(o["footprint"]) for o in objs
            if o["kind"] == "building" and o["name"] == "TOWN_CENTER" and "footprint" in o}
    dead = {o["uuid"] for o in objs if o["kind"] == "unit" and o["name"].startswith("VILLAGER") and "uuid" in o}
    for u in sorted(gone):
        g.command(f"aoe destroy {u}")
    for u in sorted(dead):
        g.command(f"kill {u}")
    for x in [g, *(b.g for b in getattr(g, "bots", ()))]:
        x.sieged |= gone & x.forts.keys()
        x.villagers = {u: v for u, v in x.villagers.items() if u not in dead}
        x.units = [o for o in x.units if o.get("uuid") not in dead]
        x.enemies = {u: k for u, k in x.enemies.items() if u not in dead}
        if isinstance(x.stock, gather.Endless):
            continue
        for r in MODE.get("none", ()):
            x.stock[r] = 0
            x.command(f"scoreboard players set {r.title()} {x.board} 0")   # the sidebar (Gather.setup)


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
