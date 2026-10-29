"""
The stance menu of the selected military units (#1107, owner decision A of #1106): a right click on a selected military
unit opens a chest menu (menu.py), as a right click on a selected villager opens the build menu (#621). A click on one
of the four AoE2 stances sends `aoe stance` (combat.stance_command, #1104) to each selected military unit, not to the
villagers, and closes the menu. The fifth item selects all units of the type near the clicked unit: the second click
did that before (#743). The sixth item stops the selected military units at once (#3353). The seventh item
sends them on a patrol to the next clicked ground cell (#3355). The eighth item is the Attack Move (#3357), the ninth and
tenth are Follow and Guard (follow.py, #3358). The eleventh item deletes the selected own units (#3451). The twelfth
item, for a scout only, gives the selected scouts the Auto Scout order (autoscout.py, #3703). The thirteenth item lets
the selected siege units shoot at the next clicked ground cell (Attack Ground, #4079).
The boss bar of the selected unit shows a stance other than aggressive (bossbar.py).
"""
import json
import math

import autoscout
import bossbar
import menu as chest
import scout

# The stances of combat.STANCES with their item and the AoE2 text.
ITEMS = (("aggressive", "iron_sword", "Aggressive", "Attacks enemies in sight and chases them"),
         ("defensive", "shield", "Defensive", "Chases an enemy a short way, then walks back"),
         ("stand_ground", "iron_bars", "Stand Ground", "Attacks only enemies in range and keeps its place"),
         ("no_attack", "white_banner", "No Attack", "Never attacks without an order"))
TYPE = len(ITEMS)                                                  # slot: select all of the type (#743)
STOP = TYPE + 1                                                    # slot: stop the selected military units (#3353)
PATROL = STOP + 1                                                  # slot: patrol to a clicked point (#3355)
ATTACK_MOVE = PATROL + 1                                           # slot: walk to a clicked point, attack on the way (#3357)
FOLLOW = ATTACK_MOVE + 1                                           # slot: follow a clicked unit (#3358)
GUARD = FOLLOW + 1                                                 # slot: guard a clicked unit or building (#3358)
DELETE = GUARD + 1                                                 # slot: kill the selected own units (#3451)
AUTO_SCOUT = DELETE + 1                                            # slot: explore the map by itself, scouts only (#3703)
ATTACK_GROUND = AUTO_SCOUT + 1                                     # slot: siege units shoot at a clicked point (#4079)
SCOUT_NAMES = {scout.CAVALRY, *scout.SCOUTS.values()}              # the unit names that get the item
FORMATION = 18                                                     # third row: the four formations of AoE2 (#3416)
FORMATIONS = (("Line", "rail", "Units in rows across the walk"),
              ("Box", "oak_fence", "Melee units around the ranged and weak units"),
              ("Staggered", "iron_chain", "Rows with double gaps, against area damage"),
              ("Flank", "arrow", "Two groups side by side with a gap"))


def stance(g, uuid):
    return getattr(g, "stances", {}).get(uuid, "aggressive")


def formation(g, uuid):
    return getattr(g, "formations", {}).get(uuid, "Line")


def items(g, uuid):
    now, form = stance(g, uuid), formation(g, uuid)
    return [(i, item, name, text + "\nNow" * (s == now)) for i, (s, item, name, text) in enumerate(ITEMS)] + \
        [(TYPE, "spyglass", "Select All of the Type", "The units of this type near it"),
         (STOP, "barrier", "Stop", "Stops the units at once"),
         (PATROL, "compass", "Patrol", "Walk between here and a point; attack the enemies on the way"),
         (ATTACK_MOVE, "iron_axe", "Attack Move", "Walk to a point; attack each enemy on the way"),
         (FOLLOW, "lead", "Follow", "Walk after an own unit and stay near it"),
         (GUARD, "bell", "Guard", "Stay near an own unit or building; attack the enemies near it"),
         (DELETE, "tnt", "Delete", "Kills the selected units")] + \
        ([(AUTO_SCOUT, "filled_map", "Auto Scout", "Explores the map by itself")] if getattr(g, "soldiers", {}).get(uuid) in SCOUT_NAMES else []) + \
        [(ATTACK_GROUND, "fire_charge", "Attack Ground", "Siege units shoot at a point on the ground")] + \
        [(FORMATION + i, item, k, text + "\nNow" * (k == form)) for i, (k, item, text) in enumerate(FORMATIONS)]


def open_menu(g, player, uuid):
    """Show the stance menu for the selection; uuid is the clicked unit."""
    def choose(p, slot, shift):
        if slot < TYPE:
            put(g, ITEMS[slot][0])
        elif slot == TYPE:
            g.select_type(uuid)
        elif slot == STOP:
            stop(g)
        elif slot == PATROL:
            vars(g).setdefault("ordering", {})[p] = "patrol"                                # the next right click picks the point
        elif slot == ATTACK_MOVE:
            vars(g).setdefault("ordering", {})[p] = "attack_move"
        elif slot in (FOLLOW, GUARD):
            vars(g).setdefault("ordering", {})[p] = "follow" if slot == FOLLOW else "guard"   # the next click picks the target
        elif slot == DELETE:
            delete(g)
        elif slot == AUTO_SCOUT:
            auto_scout(g, p)
        elif slot == ATTACK_GROUND:
            if siege(g):
                vars(g).setdefault("ordering", {})[p] = "attack_ground"                     # the next right click picks the point
            else:
                g.command(f"title {p} actionbar " + json.dumps({"text": packed_hint(g) or "No unit can attack the ground"}))
        elif FORMATION <= slot < FORMATION + len(FORMATIONS):
            form(g, p, FORMATIONS[slot - FORMATION][0])
        else:
            return
        chest.close(g, p)
    return chest.show(g, player, "Stance", items(g, uuid), choose)


def put(g, s):
    """Give each selected military unit the stance s."""
    import combat                                                  # combat imports gather, gather imports this module
    for u in sorted(g.selected):
        if u in g.soldiers:
            g.command(combat.stance_command(u, s))
            g.stances.pop(u, None) if s == "aggressive" else g.stances.update({u: s})
    if getattr(g, "bar", None) in g.selected:
        bossbar.show(g, g.bar)


def form(g, player, kind):
    """Give each selected military unit the formation kind of its next walks (Gather.walk_to); Line is no entry."""
    import json
    f = vars(g).setdefault("formations", {})
    for u in sorted(g.selected):
        if u in g.soldiers:
            f.pop(u, None) if kind == "Line" else f.update({u: kind})
    g.command(f"title {player} actionbar " + json.dumps({"text": f"Formation: {kind}"}))


def stop(g):
    """Stop the selected military units at once: their walk, their attack and their patrol (AoE2 Stop, #3353). A new
    order ends the old ones (Gather.new_order); the plugin stops each mob (aoe stop)."""
    units = [u for u in sorted(g.selected) if u in g.soldiers]
    for u in units:
        g.command(f"aoe stop {u}")
    g.new_order(units)


def delete(g):
    """Kill each selected own unit at once, with its horse, camel or boat, as the AoE2 Delete key (#3451): no resources
    come back. The census then finds them dead as after a fight (score, population, selection: train.census)."""
    import train                                                   # train imports gather, gather imports this module
    for u in [u for u in sorted(g.selected) if u in g.villagers or u in g.soldiers]:   # not KEEP: "Disable Object Deletion" (#3777)
        g.command(f"execute as {u} if entity @s[tag=!aoe2mc.keep] on vehicle run kill @s")
        g.command(f"execute as {u} if entity @s[tag=!aoe2mc.keep] run kill @s")
    train.census(g)


def auto_scout(g, player):
    """Give the selected scouts the Auto Scout order (autoscout.start); the other selected units keep their order."""
    import json
    autoscout.start(g, [u for u in sorted(g.selected) if g.soldiers.get(u) in SCOUT_NAMES])
    g.command(f"title {player} actionbar " + json.dumps({"text": "Auto Scout"}))


def patrol(g, player, cell):
    """Send the selected military units on a patrol between the middle of the selection and the block cell (x, z), as
    the AoE2 Patrol (#3355): a new tag aoe_patrol.<n>, one entry of g.patrols (scenario.patrol walks the legs) and the
    stance aggressive for the walk, so that the mob AI attacks the enemies on the way. A new order ends it."""
    import gather                                                  # gather imports this module
    units = [u for u in sorted(g.selected) if u in g.soldiers]
    pos = g.positions(units)
    if not pos:
        return
    g.new_order(units)
    patrols = vars(g).setdefault("patrols", [])
    tag = f"aoe_patrol.{1 + max((int(q[0][11:]) for q in patrols if q[0].startswith('aoe_patrol.')), default=0)}"
    a = [round(sum(p[i] for p in pos.values()) / len(pos)) for i in range(3)]
    b = [cell[0], g.map.y(*cell), cell[1]]
    patrols.append([tag, [b, a], 0])
    for u in pos:
        g.command(f"tag {u} add {tag}")
        g.command(f"aoe stance {u} aggressive")
        vars(g).get("stances", {}).pop(u, None)
    g.command(f"aoe moveto @e[tag={tag}] {b[0]} {b[1]} {b[2]}")
    for c in gather.marker(g.map, {tuple(cell)}, "go", player):
        g.command(c)


def attack_move(g, player, cell):
    """Send the selected military units to the clicked ground cell (x, z), as the AoE2 Attack Move (#3357): they walk
    with the stance aggressive, so that the mob AI attacks each enemy on the way. arrive() gives the old stance back at
    the point; a new order ends it (end_attack_moves)."""
    import gather                                                  # gather imports this module
    units = [u for u in sorted(g.selected) if u in g.soldiers]
    if not units:
        return
    cells = g.walk_to(player, cell, units=units) or {}             # a new order ends the old attack moves first
    moves = vars(g).setdefault("attack_moves", {})
    for u, c in cells.items():
        moves[u] = [c, g.stances.pop(u, "aggressive")]
        g.command(f"aoe stance {u} aggressive")
    for c in gather.marker(g.map, {tuple(cell)}, "go", player):
        g.command(c)


def siege(g):
    """The selected units that can attack the ground (combat.GROUND, the AoE2 list of #4078)."""
    import combat                                                  # combat imports gather, gather imports this module
    return [u for u in sorted(g.selected) if g.soldiers.get(u) in combat.GROUND and not packed(g, u)]


def packed(g, u):
    """True for a Trebuchet that is not unpacked: AoE2 lets only an unpacked Trebuchet attack the ground (#4207)."""
    import trebuchet                                               # trebuchet imports gather
    return g.soldiers.get(u) == trebuchet.NAME and trebuchet.state(g, u) != "unpacked"


def packed_hint(g):
    """The hint when a selected Trebuchet is packed, else None."""
    return "Unpack the Trebuchet first" if any(packed(g, u) for u in g.selected) else None


def attack_ground(g, player, cell):
    """The selected siege units shoot at the clicked ground cell (x, z) until a new order, as the AoE2 Attack Ground
    (#4079): `aoe attackground` of the plugin (#4078). The other selected units ignore the order."""
    import gather                                                  # gather imports this module
    if hint := packed_hint(g):
        g.command(f"title {player} actionbar " + json.dumps({"text": hint}))
    if not (units := siege(g)):
        return
    g.new_order(units)
    for u in units:
        g.command(f"aoe attackground {u} {cell[0]} {g.map.y(*cell)} {cell[1]}")
    for c in gather.marker(g.map, {tuple(cell)}, "go", player):
        g.command(c)


def restore(g, u, old):
    """Give the unit its stance old again (the stance before its attack move)."""
    g.command(f"aoe stance {u} {old}")
    g.stances.pop(u, None) if old == "aggressive" else g.stances.update({u: old})


def arrive(g):
    """Each attack move ends when its unit is near its point (or dead): the old stance comes back (#3357)."""
    moves = vars(g).get("attack_moves")
    if not moves:
        return
    pos = g.positions(list(moves))
    for u, (c, old) in list(moves.items()):
        p = pos.get(u)
        if p is None or math.hypot(p[0] - c[0] - 0.5, p[2] - c[1] - 0.5) <= 2:
            del moves[u]
            if p is not None:
                restore(g, u, old)


def end_attack_moves(g, units):
    """A new order ends the attack moves of the units: the old stance comes back at once (#3357)."""
    moves = vars(g).get("attack_moves", {})
    for u in sorted(units):
        if u in moves:
            restore(g, u, moves.pop(u)[1])
