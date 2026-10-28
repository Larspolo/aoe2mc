"""The siege tower in the game program (#1362, epic #1348). The siege workshop trains it in the Castle Age (train.py).
A right click with selected units on an own siege tower sends the infantry, the foot archers and the villagers of the
selection into it, as in AoE2 DE (AoE2 wiki "Siege Tower": garrison 10, "Infantry, foot archers, and Villagers"): they
walk to it with the plugin (`aoe moveto`), and at the tower they go in. A right click on the selected tower lets them
all out next to it. When the tower dies, they come out where they are.

Minecraft feature: the units inside ride the tower (`ride ... mount`, Minecraft riders): the first one rides its crew
(the passenger of the minecart), each next one the one before. So they move with the tower without own logic. A unit
inside has the state of a garrisoned unit (garrison.INSIDE: Invulnerable, NoAI, no name) and the plugin hides it from
the players (`aoe hide`). "Unload units over walls" is a later ticket.

    siege_tower.order(g, player, u)   # gather.Gather.click: the selection goes into the own siege tower u
    siege_tower.out(g, u)             # gather.Gather.click on the selected tower: all units come out
    siege_tower.tick(g)               # gather.Gather.step: units at the tower go in, a dead tower lets them out
"""
import json
import math

from aoe2mc import GARRISONED
from garrison import INSIDE, OUTSIDE

NAME = "SIEGE_TOWER"
SIZE = 10                   # units inside, as in AoE2
DOOR = 2.5                  # blocks from the tower: there a unit goes in


def fits(g, u):
    """True for a unit that goes into a siege tower: a villager, an infantry unit or a foot archer."""
    import civs, combat                                            # combat imports gather, gather imports this module
    if u in g.villagers:
        return True
    s = combat.stats(g.soldiers.get(u, ""))
    return combat.INF in s.classes or combat.ARC in s.classes and not civs.mounted(s)


def order(g, player, tower):
    """The units of the selection that fit walk into the own siege tower. Returns True, or False (no own tower, or
    no unit of the selection fits): the click is then not a garrison order."""
    if g.soldiers.get(tower) != NAME or not g.paper or not (pos := g.pos(tower)):
        return False
    who = sorted(u for u in g.selected - {tower} if fits(g, u))
    if not who:
        return False
    import ai, train                                               # ai and train import gather
    for u in who:
        if (v := g.villagers.get(u)) is not None:                  # the villager stops its work
            v.state, v.path, v.goal, v.site = "garrison", [], None, None
        name = "VILLAGER" if u in g.villagers else g.soldiers[u]
        ai.move(g, u, name, g.map.T, pos[0], pos[1], pos[2], ai.NORMAL * train.speed(g, name))
        vars(g).setdefault("boarding", {})[u] = tower
    g.mark(player, {(math.floor(pos[0]), math.floor(pos[2]))})
    return True


def go_in(g, u, tower):
    """Unit u rides the siege tower: on its crew, or on the last unit inside. A full tower: it stays next to it."""
    units = vars(g).setdefault("towers", {}).setdefault(tower, [])
    g.command(f"aoe stop {u}")
    if len(units) >= SIZE:
        if (v := g.villagers.get(u)) is not None:
            v.state = "idle"
        return
    ride = f"ride {u} mount {units[-1]}" if units else f"execute as {tower} on passengers run ride {u} mount @s"
    for c in (ride, f"data merge entity {u} {INSIDE}", f"tag {u} add {GARRISONED}", f"aoe hide @a {u}"):
        g.command(c)
    units.append(u)
    if (v := g.villagers.get(u)) is not None:
        v.state = "garrison"
    if u in g.selected:                                            # it leaves the selection
        g.choose(g.selected - {u}, min(g.selected - {u}, default=None))


def out(g, tower, pos=None):
    """All units of the siege tower come out on the free cells next to it (pos: its feet, else read). Returns them."""
    units = vars(g).get("towers", {}).pop(tower, [])
    pos = pos or g.pos(tower)
    if not units or not pos:
        return units
    cell = (math.floor(pos[0]), math.floor(pos[2]))
    ring = sorted(g.map.around({cell}), key=lambda c: (math.dist(c, cell), c)) or [cell]
    for k, u in enumerate(reversed(units)):                        # the top of the stack first
        x, z = ring[k % len(ring)]
        y = g.map.y(x, z) or pos[1]
        for c in (f"ride {u} dismount", f"tp {u} {x + 0.5} {y} {z + 0.5}", f"data merge entity {u} {OUTSIDE}",
                  f"tag {u} remove {GARRISONED}", f"aoe show @a {u}", f"aoe label {u}"):
            g.command(c)
        if (v := g.villagers.get(u)) is not None:
            v.pos, v.state = (x + 0.5, float(y), z + 0.5), "idle"
    g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": f"{len(units)} units came out", "color": "gray"}))
    return units


def tick(g):
    """The units next to their siege tower go in; the units of a dead tower come out where they are."""
    boarding, towers = vars(g).get("boarding", {}), vars(g).get("towers", {})
    if boarding:
        pos = g.positions(sorted(set(boarding) | set(boarding.values())))
        for u, tower in sorted(boarding.items()):
            if u not in pos or tower not in pos or g.soldiers.get(tower) != NAME:
                del boarding[u]                                    # dead, or the tower died
            elif math.dist((pos[u][0], pos[u][2]), (pos[tower][0], pos[tower][2])) <= DOOR:
                del boarding[u]
                go_in(g, u, tower)
    for tower in [t for t in sorted(towers) if t not in g.soldiers]:   # dead: the riders fall off where it stood
        units = towers[tower]
        out(g, tower, next((p for u in units if (p := g.pos(u))), None))
