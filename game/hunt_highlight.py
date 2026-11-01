"""
The switch "Highlight huntable animals" of the Game menu (#5509). An extra, not AoE2 (P3: opt-in, off by default): a
click turns it on or off for the player who clicked. On: the huntable animals of Gaia (deer, boar, sheep: the animals
with food of gather.HUNT_FOOD) glow for that player only. The vanilla effect glowing shows to all players, so the Paper
plugin sends it to one client (`aoe huntglow`, HuntGlow.java).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402
from rcon import MAX  # noqa: E402


def on(g, player):
    """True when the switch is on for player."""
    return player in getattr(g, "hunt_highlight", set())


def animals(g):
    """The UUIDs of the huntable animals of Gaia that are still alive, sorted."""
    skip = set(getattr(g, "dead", {})) | set(getattr(g, "flock", ()))   # own herdables are not of Gaia
    return sorted(u for u, n in getattr(g, "prey", {}).items() if gather.hunt_food(n) and u not in skip)


def commands(player, uuids, limit=MAX):
    """The plugin commands that make uuids glow for player, each at most limit bytes: `on` first, then `add`."""
    out = [f"aoe huntglow {player} on"]
    for u in uuids:
        if len(f"{out[-1]} {u}".encode()) > limit:
            out.append(f"aoe huntglow {player} add")
        out[-1] += " " + u
    return out


def toggle(g, player):
    """Turn the switch of player on or off. Returns the new state."""
    g.hunt_highlight = getattr(g, "hunt_highlight", set()) ^ {player}
    state = on(g, player)
    for c in commands(player, animals(g)) if state else [f"aoe huntglow {player} off"]:
        g.command(c)
    return state


def button(g, player):
    """The button of the Game menu: its material, name and lore with the state."""
    return ("glow_ink_sac", "Highlight huntable animals", f"Now {'on' if on(g, player) else 'off'}. Click to change.")
