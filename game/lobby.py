"""
The page "Choose your player" of the Game menu in a game of more people (#1563, decision #1308: option C later), as in
the AoE2 lobby: each Minecraft player chooses its AoE2 player. The join order of run.Game.side stays the default. One
wool for each AoE2 player 1 ... people; a side that another Minecraft player has is taken. A choice moves the Minecraft
player to the team p<n> (run.Game.choose), so its clicks go to the Gather of player n (Gather.who, #1310).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import player_color  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import menu  # noqa: E402

SLOT = 2                                                           # the slot of the button in the Game menu
BUTTON = ("player_head", "Choose your player", "Play another AoE2 player.")


def shown(g):
    """True in a game of more people (run.py --people)."""
    return getattr(getattr(g, "game", None), "people", 1) > 1


def name(g, n):
    civ = getattr(g, "trigger_civs", {}).get(str(n)) or build.pretty(g.players.get(str(n), {}).get("civ") or "")
    return f"Player {n}" + (f" ({civ})" if civ else "")              # a scenario trigger renames it (#2905)


def items(g, player):
    """Slot n - 1: the wool of the color of player n, its name and who has it."""
    out = []
    for n in range(1, g.game.people + 1):
        color = g.players.get(str(n), {}).get("color") or player_color(n)
        who = sorted(p for p, k in g.game.sides.items() if k == n)
        lore = "You" if player in who else f"Taken by {who[0]}" if who else "Free"
        out.append((n - 1, f"{color}_wool", name(g, n), lore))
    return out


def show(g, player):
    menu.show(g, player, "Choose your player", items(g, player), lambda p, slot, shift: choose(g, p, slot + 1))


def choose(g, player, n):
    """Give Minecraft player `player` the AoE2 player n when no other one has it. Returns True on a change."""
    if not 1 <= n <= g.game.people or g.game.sides.get(player) == n:
        return False
    if not g.game.choose(player, n):
        build.say(g, player, f"{name(g, n)} is taken.")
        return False
    menu.close(g, player)
    g.command(f"tellraw {player} " + json.dumps({"text": f"You play {name(g, n)}.", "color": "gold"}))
    return True
