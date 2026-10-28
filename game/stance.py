"""
The stance menu of the selected military units (#1107, owner decision A of #1106): a right click on a selected military
unit opens a chest menu (menu.py), as a right click on a selected villager opens the build menu (#621). A click on one
of the four AoE2 stances sends `aoe stance` (combat.stance_command, #1104) to each selected military unit, not to the
villagers, and closes the menu. The fifth item selects all units of the type near the clicked unit: the second click
did that before (#743). The sixth item stops the selected military units at once (#3353).
The boss bar of the selected unit shows a stance other than aggressive (bossbar.py).
"""
import bossbar
import menu as chest

# The stances of combat.STANCES with their item and the AoE2 text.
ITEMS = (("aggressive", "iron_sword", "Aggressive", "Attacks enemies in sight and chases them"),
         ("defensive", "shield", "Defensive", "Chases an enemy a short way, then walks back"),
         ("stand_ground", "iron_bars", "Stand Ground", "Attacks only enemies in range and keeps its place"),
         ("no_attack", "white_banner", "No Attack", "Never attacks without an order"))
TYPE = len(ITEMS)                                                  # slot: select all of the type (#743)
STOP = TYPE + 1                                                    # slot: stop the selected military units (#3353)


def stance(g, uuid):
    return getattr(g, "stances", {}).get(uuid, "aggressive")


def items(g, uuid):
    now = stance(g, uuid)
    return [(i, item, name, text + "\nNow" * (s == now)) for i, (s, item, name, text) in enumerate(ITEMS)] + \
        [(TYPE, "spyglass", "Select All of the Type", "The units of this type near it"),
         (STOP, "barrier", "Stop", "Stops the units at once")]


def open_menu(g, player, uuid):
    """Show the stance menu for the selection; uuid is the clicked unit."""
    def choose(p, slot, shift):
        if slot < TYPE:
            put(g, ITEMS[slot][0])
        elif slot == TYPE:
            g.select_type(uuid)
        elif slot == STOP:
            stop(g)
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


def stop(g):
    """Stop the selected military units at once: their walk, their attack and their patrol (AoE2 Stop, #3353). A new
    order ends the old ones (Gather.new_order); the plugin stops each mob (aoe stop)."""
    units = [u for u in sorted(g.selected) if u in g.soldiers]
    for u in units:
        g.command(f"aoe stop {u}")
    g.new_order(units)
