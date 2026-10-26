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
The end and destroy codes (#819): "i r winner" and "resign" show the title "Victory" or "Defeat" to all players and set
g.ended, which ends gather.Gather.run. "torpedo<n>" destroys player n, "black death" all other players (AoE2 has a bug
here: it kills only one player) and "wimpywimpywimpy" the own player (a defeat). The buildings of the player fall as
at 0 hit points (the plugin, `aoe destroy`), its units die (`kill` with the team and the tag of the player, #358).
"natural wonders" gives the control of the Gaia animals and takes the control of the own units (not reversible).
"""
import re
from urllib.parse import quote

OBJECTIVE = "aoe_cheat"
ALL = {"food": 100000, "wood": 100000, "gold": 100000, "stone": 100000}
MAP = "The map is open already: Minecraft has no fog of war."


def aegis(g, player):
    g.aegis = not g.aegis
    g.command(f'tellraw {player} {{"text":"Aegis {"on" if g.aegis else "off"}"}}')


def end(text, color):
    def effect(g, player):
        g.command(f'title @a title {{"text":"{text}","color":"{color}"}}')
        g.ended = text
    return effect


def destroy(g, n):
    """Destroy all units and buildings of player n."""
    g.command(f"aoe destroy @e[tag=aoe2mc.building,team=p{n}]")
    g.command(f"execute as @e[tag=aoe2mc.p{n}] on vehicle run kill @s")   # the horse, elephant or boat of a unit
    g.command(f"kill @e[team=p{n},type=!player]")
    g.command(f"kill @e[tag=aoe2mc.p{n}]")                        # units that the team pulse did not reach yet
    import combat
    gone = {combat.target_uuid(o["footprint"]) for o in g.data["objects"]
            if o["kind"] == "building" and o["player"] == n and "footprint" in o}
    g.sieged |= gone & g.forts.keys()                              # Gather.fall frees their footprints
    if n == g.player:
        g.choose(set())
        g.villagers, g.soldiers = {}, {}
    else:
        dead = {o.get("uuid") for o in g.data["objects"] if o["player"] == n}
        g.enemies = {u: k for u, k in g.enemies.items() if u not in dead}


def others(g):
    return sorted({o["player"] for o in g.data["objects"] if o["player"] not in (0, g.player)})


def wonders(g, player):
    g.choose(set())
    g.villagers = {}
    g.soldiers = {o["uuid"]: o["name"] for o in g.data["objects"] if o["kind"] == "unit" and o["player"] == 0
                  and o.get("uuid")}
    g.command(f'tellraw {player} {{"text":"You control nature: {len(g.soldiers)} animals"}}')


CODES = {                                     # code -> the resources that it gives, the chat answer or a function
    "aegis": aegis,
    "black death": lambda g, player: [destroy(g, n) for n in others(g)],
    "cheese steak jimmy's": {"food": 10000},
    "i r winner": end("Victory", "gold"),
    "lumberjack": {"wood": 10000},
    "marco": MAP,
    "natural wonders": wonders,
    "ninjaconnor": ALL,
    "ninjalui": ALL,
    "polo": MAP,
    "resign": end("Defeat", "red"),
    "robin hood": {"gold": 10000},
    "rock on": {"stone": 10000},
    "rowshep": ALL,
    "torpedo1": lambda g, player: destroy(g, 1),
    "torpedo2": lambda g, player: destroy(g, 2),
    "torpedo3": lambda g, player: destroy(g, 3),
    "torpedo4": lambda g, player: destroy(g, 4),
    "torpedo5": lambda g, player: destroy(g, 5),
    "torpedo6": lambda g, player: destroy(g, 6),
    "torpedo7": lambda g, player: destroy(g, 7),
    "torpedo8": lambda g, player: destroy(g, 8),
    "wimpywimpywimpy": lambda g, player: destroy(g, g.player) or end("Defeat", "red")(g, player),
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
