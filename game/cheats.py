"""
The AoE2 cheat codes in the chat of the game program (#816, epic #820). With `game/run.py --play --cheats`, as the
cheats setting of the AoE2 lobby (off by default), setup() gives the codes to the Paper plugin (`aoe cheats`,
game/plugin Cheats.java): a chat text that is a code (also "/code") does not go to the chat, and sets the score
aoe_cheat of the player to the number of the code in NAMES (1 = the first). gather.Gather.clicks calls clicks(): it
reads and resets the score and does the effect. Vanilla has no event for a chat text, so the plugin is necessary.
The codes and amounts of AoE2 DE: the AoE2 wiki, "Cheat code (Age of Empires II)" (10,000 of one resource since
The Forgotten, before it 1,000). Minecraft has no fog of war: "marco" and "polo" only answer in the chat.
"""
import re
from urllib.parse import quote

OBJECTIVE = "aoe_cheat"
ALL = {"food": 100000, "wood": 100000, "gold": 100000, "stone": 100000}
MAP = "The map is open already: Minecraft has no fog of war."
CODES = {                                     # code -> the resources that it gives, or the chat answer
    "cheese steak jimmy's": {"food": 10000},
    "lumberjack": {"wood": 10000},
    "marco": MAP,
    "ninjaconnor": ALL,
    "ninjalui": ALL,
    "polo": MAP,
    "robin hood": {"gold": 10000},
    "rock on": {"stone": 10000},
    "rowshep": ALL,
}
NAMES = sorted(CODES)                         # the score of a code is its index + 1


def setup(g):
    """Turn the cheats on in the plugin when g.cheats is true. Without cheats the plugin knows no code."""
    if g.cheats:
        g.command(f'scoreboard objectives add {OBJECTIVE} dummy "Cheat"')
        g.command("aoe cheats " + ",".join(quote(c, safe="") for c in NAMES))


def apply(g, player, code):
    effect = CODES[code]
    if isinstance(effect, str):
        g.command(f'tellraw {player} {{"text":"{effect}"}}')
        return
    for r, v in effect.items():
        g.stock[r] += v
        g.command(f"scoreboard players add {r.capitalize()} aoe_res {v}")


def clicks(g):
    """Do the cheat of each player who typed a code since the last call. Returns the (player, code) pairs."""
    if not g.cheats or "passed" not in g.command(f"execute if entity @a[scores={{{OBJECTIVE}=1..}}]"):
        return []
    out = []
    for player in (n.strip() for n in g.command("list").split(":", 1)[-1].split(",")):
        m = player and re.search(r" has (\d+) ", g.command(f"scoreboard players get {player} {OBJECTIVE}"))
        if m and 0 < int(m.group(1)) <= len(NAMES):
            g.command(f"scoreboard players reset {player} {OBJECTIVE}")
            out.append((player, NAMES[int(m.group(1)) - 1]))
            apply(g, *out[-1])
    return out
