"""
The "Go to" compass of the game program (#1830, owner decision B of #1828: a compass menu; the F key stays free). A
hotbar item (ITEM, in hotbar slot SLOT) opens a chest menu (menu.py) with the places that the AoE2 keys go to: each own
town center (H), each saved control group (a double press of its number) and the next idle villager ("."). A click puts
the player above the place, facing it, with the plugin command `aoe view` (the view of the attack alerts, Alerts.view,
#1816), and closes the menu. A click on a group also selects the group, a click on "Idle villager" selects the villager.
An item with no place (no town center, an empty group, no idle villager) is gray and does nothing.
gather.Gather.clicks gives the item and opens the menu.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu  # noqa: E402
import train  # noqa: E402

SLOT = 2                                                           # hotbar slot of the item (key 3): free (#1830)
ITEM = ('minecraft:carrot_on_a_stick[item_model="minecraft:compass",item_name="Go to",'
        "custom_data={aoe_goto:1b}]")
TITLE = "Go to"
GRAY = "gray_dye"                                                  # an item with no place
CENTERS = 9                                                        # row 0: the town centers
GROUP_ROW = 9                                                      # row 1: group n in slot GROUP_ROW + n - 1
IDLE = 18                                                          # row 2: the next idle villager


def give(g):
    """Put the item into hotbar slot SLOT of each player that has no "Go to" item there."""
    g.command(f"execute as {g.who} unless items entity @s hotbar.{SLOT} *[custom_data={{aoe_goto:1b}}] "
              f"run item replace entity @s hotbar.{SLOT} with {ITEM}")


def in_hand(g, player):
    """True when player holds the "Go to" item in the main hand."""
    return "passed" in g.command(f"execute if items entity {player} weapon.mainhand *[custom_data={{aoe_goto:1b}}]")


def centers(g):
    """The (x, z) block centers of the own complete town centers, in footprint order."""
    return [((x0 + x1) / 2, (z0 + z1) / 2) for (x0, x1, z0, z1), name in sorted(train.homes(g).items())
            if name == "TOWN_CENTER"][:CENTERS]


def idle(g):
    """The UUIDs of the idle villagers, sorted."""
    return sorted(u for u, v in g.villagers.items() if v.state == "idle")


def items(g):
    """The menu items (slot, material, name, lore, count)."""
    import gather
    tcs = centers(g)
    out = [(i, "bell", f"Town center {i + 1}", "Go to this town center.", 1) for i in range(len(tcs))] \
        or [(0, GRAY, "Town center", "No own town center.", 1)]
    for n, (_, dye) in gather.GROUPS.items():
        k = len(g.groups.get(n, ()))
        out.append((GROUP_ROW + n - 1, dye if k else GRAY, f"Group {n}: {k} units",
                    "Select the group and go to it." if k else "Save a group with a shift right click.", min(max(k, 1), 64)))
    k = len(idle(g))
    out.append((IDLE, "wooden_hoe" if k else GRAY, "Idle villager",
                f"{k} idle: go to the next one and select it." if k else "No idle villager.", min(max(k, 1), 64)))
    return out


def open_menu(g, player):
    g.person = player                                                  # the groups of this person (#3490)
    menu.show(g, player, TITLE, items(g), lambda p, slot, shift: button(g, p, slot))


def view(g, player, x, z):
    """Put player above the block x, z, facing it, in free air (the plugin, Alerts.view), and close the menu."""
    menu.close(g, player)
    g.command(f"aoe view {player} {x:.1f} {z:.1f}")


def button(g, player, slot):
    """A click on the menu: go to the place of the item. Returns the (x, z) of the place, or None (a gray item)."""
    tcs = centers(g)
    g.person = player                                                  # the groups of this person (#3490)
    if slot < len(tcs):
        at = tcs[slot]
    elif (n := slot - GROUP_ROW + 1) in g.groups and g.groups[n]:
        g.group(player, n, False)                                      # select the live units of the group
        pos = g.positions(sorted(g.selected)) if g.selected else {}
        if not pos:
            return None
        at = (lambda p: (p[0], p[2]))(pos[min(pos)])                 # the unit of the boss bar (Gather.group)
    elif slot == IDLE and (uuids := idle(g)):
        state = vars(g).setdefault("goto_idle", {})
        u = next((u for u in uuids if u > state.get(player, "")), uuids[0])   # the next one at each click (".")
        state[player] = u
        g.select(u)
        at = (g.villagers[u].pos[0], g.villagers[u].pos[2])
    else:
        return None
    view(g, player, *at)
    return at
