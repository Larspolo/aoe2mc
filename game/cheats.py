"""
The AoE2 cheat codes in the chat of the game program (#816, epic #820). With `game/run.py --play --cheats`, as the
cheats setting of the AoE2 lobby (off by default), setup() gives the codes to the Paper plugin (`aoe cheats`,
game/plugin Cheats.java): a chat text that is a code (also "/code") does not go to the chat, and sets the score
aoe_cheat of the player to the number of the code in NAMES (1 = the first). gather.Gather.clicks calls clicks(): it
reads and resets the score and does the effect. Vanilla has no event for a chat text, so the plugin is necessary.
The codes and amounts of AoE2 DE: the AoE2 wiki, "Cheat code (Age of Empires II)" (10,000 of one resource since
The Forgotten, before it 1,000). Minecraft has no fog of war: "marco" and "polo" only answer in the chat.
"aegis" (#817) is a toggle: g.aegis makes building (gather.Gather.step), training and research (train.tick) and
gathering (gather.Gather.work_time) instant, for all players as in AoE2.
A unit cheat (#818; the DE list of the wiki, "Units") summons its unit at the town center of the player, as a trained
unit (train.spawn): it costs nothing and counts in the population. Without a town center no unit appears, as in AoE2.
"""
import re
from collections import namedtuple
from urllib.parse import quote

Unit = namedtuple("Unit", "name")             # the effect of a unit cheat

OBJECTIVE = "aoe_cheat"
ALL = {"food": 100000, "wood": 100000, "gold": 100000, "stone": 100000}
MAP = "The map is open already: Minecraft has no fog of war."


def aegis(g, player):
    g.aegis = not g.aegis
    g.command(f'tellraw {player} {{"text":"Aegis {"on" if g.aegis else "off"}"}}')


CODES = {                                     # code -> the resources, the chat answer, a function or a Unit
    "aegis": aegis,
    "alpaca simulator": Unit("ALFRED_THE_ALPACA"),
    "catzor": Unit("SHARKATZOR"),
    "cheese steak jimmy's": {"food": 10000},
    "furious the monkey boy": Unit("FURIOUS_THE_MONKEY_BOY"),
    "how do you turn this on": Unit("COBRA_CAR"),
    "i don't exist": Unit("WAR_PENGUIN"),
    "i love the monkey head": Unit("VMDL"),
    "lumberjack": {"wood": 10000},
    "marco": MAP,
    "ninjaconnor": ALL,
    "ninjalui": ALL,
    "photon man": Unit("PHOTONMAN"),
    "polo": MAP,
    "robin hood": {"gold": 10000},
    "rock on": {"stone": 10000},
    "rowshep": ALL,
    "to smithereens": Unit("SABOTEUR"),
}
NAMES = sorted(CODES)                         # the score of a code is its index + 1


def setup(g):
    """Turn the cheats on in the plugin when g.cheats is true. Without cheats the plugin knows no code."""
    if g.cheats:
        g.command(f'scoreboard objectives add {OBJECTIVE} dummy "Cheat"')
        g.command("aoe cheats " + ",".join(quote(c, safe="") for c in NAMES))


def apply(g, player, code):
    effect = CODES[code]
    if callable(effect):
        return effect(g, player)
    if isinstance(effect, Unit):
        import train                                                # train -> gather -> cheats: import it late
        tc = sorted(r for r, n in train.homes(g).items() if n == "TOWN_CENTER")
        if tc:
            train.spawn(g, tc[0], effect.name)
        return
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
