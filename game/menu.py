"""
Chest menus in the game program (#619, part of #618). Vanilla has no clickable item menu, so the Paper plugin
(game/plugin) opens one: `aoe menu <player> <title> <slot>:<material>:<name>:<lore> ...` shows the items in an
inventory, and a click on an item sets the score aoe_menu of the player to slot + 1 (a shift click: -(slot + 1)). The player takes no item, and the
menu stays open, so a second click queues one more (owner, 2026-10-26). `aoe menu-close <player>` closes it.
The texts are URL-encoded: RCON splits the arguments at spaces, and ":" splits the fields of an item.
gather.Gather.clicks calls clicks(): it reads and resets the score and calls the handler of the open menu.
"""
import re
from urllib.parse import quote

OBJECTIVE = "aoe_menu"


def setup(g):
    g.command(f'scoreboard objectives add {OBJECTIVE} dummy "Menu"')


def command(player, title, items):
    """The plugin command that opens a menu. items: (slot, material, name, lore) or (slot, material, name, lore,
    count) with lore "" for none, and lines of the lore split by a new line. count: the item count (#706)."""
    def q(s):
        return quote(str(s), safe="")
    return " ".join([f"aoe menu {player} {q(title)}"] +
                    [f"{int(slot)}:{material.removeprefix('minecraft:')}:{q(name)}:{q(lore)}"
                     + (f":{int(more[0])}" if more and more[0] != 1 else "")
                     for slot, material, name, lore, *more in items])


def show(g, player, title, items, handler):
    """Open (or refresh) a menu for player; handler(player, slot, shift) gets each click."""
    g.menus[player] = handler
    return g.command(command(player, title, items))


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
            slot = abs(int(m.group(1))) - 1
            out.append((player, slot))
            handler(player, slot, int(m.group(1)) < 0)
    return out
