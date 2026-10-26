"""
The AoE2 cheat codes in the chat of the game program (#816, epic #820). With `game/run.py --play --cheats`, as the
cheats setting of the AoE2 lobby (off by default), setup() gives the codes to the Paper plugin (`aoe cheats`,
game/plugin Cheats.java): a chat text that is a code (also "/code") does not go to the chat, and sets the score
aoe_cheat of the player to the number of the code in NAMES (1 = the first). gather.Gather.clicks calls clicks(): it
reads and resets the score and does the effect. Vanilla has no event for a chat text, so the plugin is necessary.
The codes and amounts of AoE2 DE: the AoE2 wiki, "Cheat code (Age of Empires II)" (10,000 of one resource since
The Forgotten, before it 1,000). Minecraft has no fog of war: "polo" only answers in the chat, and "marco" answers
"polo", an easter egg with the name of the owner (Larspolo, #1057).
"aegis" (#817) is a toggle: g.aegis makes building (gather.Gather.step), training and research (train.tick) and
gathering (gather.Gather.work_time) instant, and a hunted animal dies at the first hit (gather.Gather.strike, #1058), for
all players as in AoE2.
A unit cheat (#818; the DE list of the wiki, "Units") summons its unit at the town center of the player, as a trained
unit (train.spawn): it costs nothing and counts in the population. Without a town center no unit appears, as in AoE2.
The end and destroy codes (#819): "i r winner" and "resign" show the title "Victory" or "Defeat" to all players and set
g.ended, which ends gather.Gather.run. "torpedo<n>" destroys player n, "black death" all other players (AoE2 has a bug
here: it kills only one player) and "wimpywimpywimpy" the own player (a defeat). The buildings of the player fall as
at 0 hit points (the plugin, `aoe destroy`), its units die (`kill` with the team and the tag of the player, #358).
A transformation cheat (#967) turns each own unit of its "from" kind into its "to" unit: the new unit appears at the place
of the old one with the same share of hit points, and the old one (with its riders) goes. The selection keeps the rest.
"natural wonders" gives the control of the Gaia animals and takes the control of the own units (not reversible).
More codes (#968): "woof woof" turns the birds into Stormy Dogs of Gaia, "my cpu can handle it" raises the highest
population limit to 1000, "tech tech one two free" makes technologies free, "going above and beyond" lets the player
research a technology up to train.REPEAT times with stacked effects (train.count), and "noui" hides the sidebar, the boss
bar and the hints, or shows them again.
Excluded and partial codes (owner, #820, #985):
- "!mute", "!nomute": excluded. The game program has no taunts, so the codes have nothing to silence.
- "marco", "polo": done as they are. Minecraft has no fog of war, so the codes only answer in the chat ("marco": "polo").
- "sharing is caring": waits for allies (#969). The game program has no allies yet.
"""
import os
import re
import sys
from collections import namedtuple
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bossbar  # noqa: E402
from units import is_bird  # noqa: E402

Unit = namedtuple("Unit", "name")             # the effect of a unit cheat
Transform = namedtuple("Transform", "to units")   # a transformation cheat: own units with units(name) become unit `to`

OBJECTIVE = "aoe_cheat"
ALL = {"food": 100000, "wood": 100000, "gold": 100000, "stone": 100000}
MAP = "The map is open already: Minecraft has no fog of war."
CAMELS = {"BACTRIAN_CAMEL", "CAMEL", "CAMEL_ARCHER", "CAMEL_RIDER", "ELITE_CAMEL_ARCHER", "HEAVY_CAMEL_RIDER",
          "IMPERIAL_CAMEL_RIDER"}               # "cameleon": not the Mameluke, Camel Scout and Raider, camel heroes
NUMBER = r"-?\d+(?:\.\d+)?"


def aegis(g, player):
    g.aegis = not g.aegis
    g.command(f'tellraw {player} {{"text":"Aegis {"on" if g.aegis else "off"}"}}')


def end(text, color):
    def effect(g, player):
        g.command(f'title @a title {{"text":"{text}","color":"{color}"}}')
        g.ended = text
        import wonder                                                  # wonder -> cheats: import it late
        wonder.close(g)
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


def flag(attr, text):
    """A cheat that turns the attribute attr of g on (for ever, as in AoE2) and answers text."""
    def effect(g, player):
        setattr(g, attr, True)
        g.command(f'tellraw {player} {{"text":"{text}"}}')
    return effect


def cpu(g, player):
    g.pop_cap = 1000
    g.command(f'tellraw {player} {{"text":"Population limit: 1000"}}')


def noui(g, player):
    """Hide the user interface of the game program (the sidebar, the boss bar, the hints), or show it again."""
    g.noui = not g.noui
    g.command("scoreboard objectives setdisplay sidebar" + f" {g.board}" * (not g.noui))
    g.command(f"bossbar set {bossbar.bar(g)} players" + " @a" * (not g.noui))


def woof(g, player):
    """Each bird becomes a Stormy Dog of Gaia on the ground under it."""
    import train                                                # train -> gather -> cheats: import it late
    for o in [o for o in g.data["objects"] if o["kind"] == "unit" and o.get("uuid") and is_bird(o["name"])]:
        if not (pos := g.pos(o["uuid"])):
            continue
        x, z = int(pos[0] // 1), int(pos[2] // 1)
        if uuid := train.summon(g, "STORMY_DOG", (x + 0.5, float(g.map.y(x, z) or pos[1]), z + 0.5), player=0):
            g.command(f"tp {o['uuid']} {pos[0]} -200 {pos[2]}")      # gone without a death and its drops
            o["name"], o["uuid"] = "STORMY_DOG", uuid
def infantry(name):
    import combat                                                  # combat imports gather, gather imports this module
    return combat.INF in combat.stats(name).classes


def villager(name):
    return name.startswith("VILLAGER")


def share(g, uuid):
    """The share of its hit points that unit uuid has: Health / max_health (1 when the server gives no number)."""
    hp = re.findall(NUMBER, g.command(f"data get entity {uuid} Health").rsplit(":", 1)[-1])
    top = re.findall(NUMBER, g.command(f"attribute {uuid} minecraft:max_health get").rsplit(" is ", 1)[-1])
    return min(1.0, float(hp[0]) / float(top[0])) if hp and top and float(top[0]) > 0 else 1.0


def transform(g, t):
    """Turn each own unit of g whose name passes t.units into unit t.to at the same place (train.summon)."""
    import train                                                   # train -> gather -> cheats: import it late
    names = {o["uuid"]: o["name"] for o in g.units if o.get("uuid") in g.villagers} | g.soldiers
    gone = set()
    for uuid, name in sorted(names.items()):
        if name == t.to or not t.units(name) or not (pos := g.pos(uuid)):
            continue
        part = share(g, uuid)
        g.command(f"execute as {uuid} on passengers run kill @s")      # the rider of a horse or camel
        g.command(f"kill {uuid}")
        g.soldiers.pop(uuid, None)
        g.villagers.pop(uuid, None)
        gone.add(uuid)
        new = train.summon(g, t.to, pos)
        if new and part < 1:
            hp = min(train.stats(g, t.to).hp, 1024)
            g.command(f"data modify entity {new} Health set value {max(1.0, round(hp * part, 1))}f")
    g.units = [o for o in g.units if o.get("uuid") not in gone]
    g.farmers = {k: u for k, u in g.farmers.items() if u not in gone}
    g.choose(g.selected - gone)


def others(g):
    return sorted({o["player"] for o in g.data["objects"] if o["player"] not in (0, g.player)})


def wonders(g, player):
    g.choose(set())
    g.villagers = {}
    g.soldiers = {o["uuid"]: o["name"] for o in g.data["objects"] if o["kind"] == "unit" and o["player"] == 0
                  and o.get("uuid")}
    g.command(f'tellraw {player} {{"text":"You control nature: {len(g.soldiers)} animals"}}')


CODES = {                                     # code -> the resources, the chat answer, a function, a Unit or a Transform
    "aegis": aegis,
    "alpaca simulator": Unit("ALFRED_THE_ALPACA"),
    "black death": lambda g, player: [destroy(g, n) for n in others(g)],
    "cameleon": Transform("FLAMING_CAMEL", CAMELS.__contains__),
    "catzor": Unit("SHARKATZOR"),
    "cheese steak jimmy's": {"food": 10000},
    "flemish reformation": Transform("MONK", villager),
    "furious the monkey boy": Unit("FURIOUS_THE_MONKEY_BOY"),
    "going above and beyond": flag("beyond", "Technologies: up to 256 researches"),
    "grab your pitchforks": Transform("FLEMISH_MILITIA", villager),
    "how do you turn this on": Unit("COBRA_CAR"),
    "i don't exist": Unit("WAR_PENGUIN"),
    "i love the monkey head": Unit("VMDL"),
    "i r winner": end("Victory", "gold"),
    "lumberjack": {"wood": 10000},
    "marco": "polo",                          # an easter egg (#1057)
    "my cpu can handle it": cpu,
    "natural wonders": wonders,
    "ninjaconnor": ALL,
    "ninjalui": ALL,
    "noui": noui,
    "photon man": Unit("PHOTONMAN"),
    "polo": MAP,
    "put on your capes": Transform("ELITE_TEUTONIC_KNIGHT", infantry),
    "resign": end("Defeat", "red"),
    "robin hood": {"gold": 10000},
    "rock on": {"stone": 10000},
    "rowshep": ALL,
    "tech tech one two free": flag("free_techs", "Technologies are free"),
    "to smithereens": Unit("SABOTEUR"),
    "torpedo1": lambda g, player: destroy(g, 1),
    "torpedo2": lambda g, player: destroy(g, 2),
    "torpedo3": lambda g, player: destroy(g, 3),
    "torpedo4": lambda g, player: destroy(g, 4),
    "torpedo5": lambda g, player: destroy(g, 5),
    "torpedo6": lambda g, player: destroy(g, 6),
    "torpedo7": lambda g, player: destroy(g, 7),
    "torpedo8": lambda g, player: destroy(g, 8),
    "wimpywimpywimpy": lambda g, player: destroy(g, g.player) or end("Defeat", "red")(g, player),
    "woof woof": woof,
    "yes we khan": Transform("GENGHIS_KHAN", {"ELITE_MANGUDAI", "MANGUDAI"}.__contains__),
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
    if isinstance(effect, Transform):
        return transform(g, effect)
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
        g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")


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
