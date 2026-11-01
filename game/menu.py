"""
Chest menus in the game program (#619, part of #618). Vanilla has no clickable item menu, so the Paper plugin
(game/plugin) opens one: `aoe menu <player> <title> <slot>:<material>:<name>:<lore> ...` shows the items in an
inventory, and a click on an item sets the score aoe_menu of the player to slot + 1 (a shift click: -(slot + 1), a right click:
slot + 1 + RIGHT, #3523). A handler with a keyword `right` gets the right click; another handler gets a normal click. The player takes no item, and the
menu stays open, so a second click queues one more (owner, 2026-10-26). `aoe menu-close <player>` closes it.
When the player closes a menu (Escape), the plugin sets the score aoe_menu_closed to 1 and clicks() forgets the handler (#5484).
The texts are URL-encoded: RCON splits the arguments at spaces, and ":" splits the fields of an item.
One RCON command holds at most rcon.MAX bytes: a longer menu goes out as `aoe menu` with the item of the last slot (it
gives the size of the inventory) and `aoe menu-add` commands with the other items (#1647).
gather.Gather.clicks calls clicks(): it reads and resets the score and calls the handler of the open menu.
"""
import inspect
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcon import MAX  # noqa: E402

OBJECTIVE = "aoe_menu"
CLOSED = "aoe_menu_closed"                                     # the player closed the menu (Escape, #5484)
RIGHT = 1000                                                   # a right click adds it (AoePlugin MENU_RIGHT, #3523)


def setup(g):
    g.command(f'scoreboard objectives add {OBJECTIVE} dummy "Menu"')
    g.command(f'scoreboard objectives add {CLOSED} dummy "Menu closed"')


def command(player, title, items):
    """The plugin command that opens a menu. items: (slot, material, name, lore) or (slot, material, name, lore,
    count) with lore "" for none, and lines of the lore split by a new line. count: the item count (#706)."""
    return " ".join([f"aoe menu {player} {q(title)}"] + [spec(it) for it in items])


def q(s):
    return quote(str(s), safe="")


def spec(item):
    """The plugin text of one item: slot:material:name:lore[:count]."""
    slot, material, name, lore, *more = item
    return (f"{int(slot)}:{material.removeprefix('minecraft:')}:{q(name)}:{q(lore)}"
            + (f":{int(more[0])}" if more and more[0] != 1 else ""))


def commands(player, title, items, limit=MAX):
    """The plugin commands of one menu, each at most limit bytes: command() when it fits, else `aoe menu` with the
    item of the last slot first (the plugin takes the size of the inventory from it) and `aoe menu-add` commands with
    the other items."""
    if len((one := command(player, title, items)).encode()) <= limit:
        return [one]
    specs = sorted((spec(it) for it in items), key=lambda s: -int(s.split(":", 1)[0]))
    out, head = [], f"aoe menu {player} {q(title)}"
    for s in specs:
        if out and len(f"{out[-1]} {s}".encode()) <= limit:
            out[-1] += " " + s
        else:
            out.append(f"{head if not out else f'aoe menu-add {player} {q(title)}'} {s}")
    return out


def lore(g, material, name, text, key=None):
    """The last lore line of each later menu item with this material and name (#1160): the plugin keeps it, so the
    menu commands stay short (one RCON command holds a whole menu). key: the translate key of the name (#5346): the
    plugin shows the name as that key with the name as fallback."""
    return g.command(f"aoe lore {material} {quote(name, safe='')} {quote(text, safe='')}" + (f" {key}" if key else ""))


def show(g, player, title, items, handler):
    """Open (or refresh) a menu for player; handler(player, slot, shift) gets each click (a handler with
    a keyword `right` also gets right=True for a right click, #3523)."""
    g.menus[player] = handler
    return [g.command(c) for c in commands(player, title, items)][0]


def close(g, player):
    g.menus.pop(player, None)
    return g.command(f"aoe menu-close {player}")


def clicks(g):
    """Call the handler of each open menu that the player clicked since the last call. Returns the (player, slot)
    pairs."""
    out = []
    for player, handler in list(g.menus.items()):
        m = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get {player} {OBJECTIVE}"))
        if m and int(m.group(1)) != 0:
            g.command(f"scoreboard players reset {player} {OBJECTIVE}")
            v = int(m.group(1))
            right = v > RIGHT
            slot = abs(v) - 1 - RIGHT * right
            out.append((player, slot))
            g.person = player                                      # the menu acts on its selection (#3486)
            if right and "right" in inspect.signature(handler).parameters:
                handler(player, slot, False, right=True)
            else:
                handler(player, slot, v < 0)
        if g.menus.get(player) is handler and " has 1 " in g.command(f"scoreboard players get {player} {CLOSED}"):
            g.command(f"scoreboard players reset {player} {CLOSED}")
            g.menus.pop(player)                                    # no refresh opens it again (train.refresh, #5484)
    return out
