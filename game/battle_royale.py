"""
The Corruption of the AoE2 DE game mode "Battle Royale" in the game program (#2439, epic #2263; run.py --mode
battle-royale): it takes the map from its border to its center in MINUTES game minutes and destroys each unit and
building that it touches (AoE2 wiki "Battle Royale"; its recommended Time is 30 minutes).
Minecraft feature: the world border shows the Corruption (the red wall and the red screen edge). It hurts only players
(Paper 26.3, #2439: a zombie and a slime outside it keep their health), and the players play in creative mode, so
tick() destroys the units and buildings outside it: four volume selectors around the border square, "aoe destroy" for a
building (it falls as at 0 hit points) and kill for the other entities of a team (units, their mounts).
gather.Gather.run gives tick() the game seconds; the border moves each EVERY game seconds, so a paused game stops it.
The rest of the mode (the Post-Imperial start with two heroes, the camps and Guardians to capture) is not here.
"""
import json

MINUTES = 30            # game minutes until the Corruption reaches the center (AoE2 wiki, the recommended "Time")
EVERY = 3.0             # game seconds between two steps of the border
FAR = 30000             # blocks: the strips outside the border reach this far


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
    """Put the world border on the map square and say how long the Corruption takes."""
    s = side(g)
    g.corruption_time, g.corruption_at = 0.0, 0.0
    for c in (f"worldborder center {s / 2:.1f} {s / 2:.1f}", "worldborder damage buffer 0", f"worldborder set {s:.1f}"):
        g.command(c)
    g.command("tellraw @a " + json.dumps({"text": f"Battle Royale: the Corruption takes the map from its border to its "
                                                  f"center in {MINUTES}:00. It destroys all units and buildings in it.",
                                          "color": "dark_red"}))
    return g


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
