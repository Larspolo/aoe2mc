"""
The AoE2 cheat codes in the chat of the game program (#816, epic #820). With `game/run.py --play --cheats`, as the
cheats setting of the AoE2 lobby (off by default), setup() gives the codes to the Paper plugin (`aoe cheats`,
game/plugin Cheats.java): a chat text that is a code (also "/code") does not go to the chat, and sets the score
aoe_cheat of the player to the number of the code in NAMES (1 = the first). gather.Gather.clicks calls clicks(): it
reads and resets the score and does the effect. Vanilla has no event for a chat text, so the plugin is necessary.
The codes and amounts of AoE2 DE: the AoE2 wiki, "Cheat code (Age of Empires II)" (10,000 of one resource since
The Forgotten, before it 1,000). "polo" removes the fog of war of the units (fog.toggle, #1390): all hidden enemy units
show; a second "polo" puts the fog back. "marco" answers "polo", an easter egg with the name of the owner (Larspolo, #1057).
"aegis" (#817) is a toggle: g.aegis makes building (gather.Gather.step), training and research (train.tick) and
gathering (gather.Gather.work_time) instant, and a hunted animal dies at the first hit (gather.Gather.strike, #1058), for
all players as in AoE2.
A unit cheat (#818; the DE list of the wiki, "Units") summons its unit at the town center of the player, as a trained
unit (train.spawn): it costs nothing and counts in the population. Without a town center no unit appears, as in AoE2.
The end and destroy codes (#819): "i r winner" shows the title "Victory" to all players and sets g.ended, which ends
gather.Gather.run. "resign" puts the own player out, and the others play on (conquest.defeat, #3105). "torpedo<n>" destroys player n, "black death" all other players (AoE2 has a bug
here: it kills only one player) and "wimpywimpywimpy" the own player (a defeat). The buildings of the player fall as
at 0 hit points (the plugin, `aoe destroy`), its units die (`kill` with the team and the tag of the player, #358).
Its construction sites (also the complete ones and those of a bot) become air, its queues empty, and its bot stops (#1657).
A transformation cheat (#967) turns each own unit of its "from" kind into its "to" unit: the new unit appears at the place
of the old one with the same share of hit points, and the old one (with its riders) goes. The selection keeps the rest.
"natural wonders" gives the control of the Gaia animals and takes the control of the own units (not reversible).
More codes (#968): "woof woof" turns the birds into Stormy Dogs of Gaia, "my cpu can handle it" raises the highest
population limit to 1000, "tech tech one two free" makes technologies free, "going above and beyond" lets the player
research a technology up to train.REPEAT times with stacked effects (train.count), and "noui" hides the sidebar, the boss
bar and the hints, or shows them again.
"sharing is caring" (#969) sends the income of the player (Gather.earn: gathering, fishing, trade, relics) to its allies
(gather.allied) in equal parts, for ever, as in AoE2. With no ally the player keeps it.
Excluded and partial codes (owner, #820, #985):
- "!mute", "!nomute": excluded. The game program has no taunts, so the codes have nothing to silence.
- "marco": done as it is. The fog of war hides only units, not the map: "marco" only answers in the chat ("polo").
"""
import os
import re
import sys
from collections import namedtuple
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bossbar  # noqa: E402
import table  # noqa: E402
from units import is_bird  # noqa: E402

Unit = namedtuple("Unit", "name")             # the effect of a unit cheat
Transform = namedtuple("Transform", "to units")   # a transformation cheat: own units with units(name) become unit `to`

OBJECTIVE = "aoe_cheat"
ALL = {"food": 100000, "wood": 100000, "gold": 100000, "stone": 100000}
FOG = {"all": "Fog of war: off", "normal": "Fog of war: on"}       # the chat answer of "polo" for each g.reveal
NUMBER = r"-?\d+(?:\.\d+)?"


def aegis(g, player):
    g.aegis = not g.aegis
    g.command(f'tellraw {player} {{"text":"Aegis {"on" if g.aegis else "off"}"}}')


def end(text, color):
    """The cheat or rule that ends the game with text ("Victory" or "Defeat") for player g.player and its allies."""
    def effect(g, player):
        import gather                                                  # gather imports cheats: import it late
        over(g, lambda n: gather.allied(g.players, g.player, n) == (text == "Victory"))
    return effect


def defeat(g, n):
    """The own player n resigns: it is out, the others play on (conquest.defeat, decision #3103)."""
    import conquest                                                    # conquest imports cheats: import it late
    conquest.defeat(g, n)


def title(g, n, text, color):
    """Show the title text to the people of player n (the team p<n>, #1936)."""
    g.command(f'title @a[team=p{n}] title {{"text":"{text}","color":"{color}"}}')


def over(g, won):
    """End the game: the team of each person gets its own title (#1936), "Victory" when won(its player), else "Defeat",
    and each Gather of the game stops (g.ended). A bot (h.share) has no Minecraft player and gets no title. Each person
    gets the recap book, and its order items go (recap.give, #2660)."""
    import fog, hill, relic_victory, time_limit, treaty, wonder       # they import cheats: import them late
    for h in fog.gathers(g):
        text, color = ("Victory", "gold") if won(h.player) else ("Defeat", "red")
        if not getattr(h, "share", None):
            title(g, h.player, text, color)
        h.ended = text
        wonder.close(h)
        relic_victory.close(h)
        hill.close(h)
        time_limit.close(h)
        treaty.close(h)
    import recap                                                       # the recap book and the end hotbar (#2660)
    recap.give(g, won)


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
    ruin(g, n)
    if n == g.player:
        g.choose(set())
        g.villagers, g.soldiers = {}, {}
    else:
        dead = {o.get("uuid") for o in g.data["objects"] if o["player"] == n}
        g.enemies = {u: k for u, k in g.enemies.items() if u not in dead}


def ruin(g, n):
    """Remove the construction sites (complete or not) and the queues of player n, also of a bot (#1657): a site has no
    target entity until it is complete, so `aoe destroy` leaves its blocks, and the queue of a bot spawns new units.
    The blocks of each site become air (above the water: a fish trap or a dock keeps it), and the bot of player n stops."""
    import combat, fleet                                           # they import gather, which imports this module
    gathers = [g, *(b.g for b in g.bots)]
    for h in gathers:
        for s in [s for s in h.sites if s["player"] == n]:
            x0, x1, z0, z1 = s["footprint"]
            bx0, y0, bz0, bx1, y1, bz1 = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
            y0 = max(y0, int(fleet.level(g)) + 1)
            g.command(f"fill {bx0} {y0} {bz0} {bx1} {y1} {bz1} minecraft:air")
            for m in {id(k.map): k.map for k in gathers}.values():    # paths go through the footprint again
                for x in range(x0, x1):
                    for z in range(z0, z1):
                        m.blocked.discard((x, z))
                        m.ground[z][x] = y0
        h.sites = [s for s in h.sites if s["player"] != n]
        if h.player == n:
            h.queues.clear()
    g.bots = [b for b in g.bots if b.g.player != n or not getattr(b.g, "share", None)]   # a person keeps its Side: over() titles it (#1936)


def flag(attr, text):
    """A cheat that turns the attribute attr of g on (for ever, as in AoE2) and answers text."""
    def effect(g, player):
        setattr(g, attr, True)
        g.command(f'tellraw {player} {{"text":"{text}"}}')
    return effect


def polo(g, player):
    """Remove the fog of war, or put it back (#1390)."""
    import fog                                                  # fog -> gather -> cheats: import it late
    g.command(f'tellraw {player} {{"text":"{FOG[fog.toggle(g)]}"}}')


def cpu(g, player):
    g.pop_cap = 1000
    g.command(f'tellraw {player} {{"text":"Population limit: 1000"}}')


def noui(g, player):
    """Hide the user interface of the game program (the sidebar, the boss bar, the hints), or show it again."""
    g.noui = not g.noui
    for slot in g.sidebars():                                   # also the team sidebar (#1309)
        g.command(f"scoreboard objectives setdisplay {slot}" + f" {g.board}" * (not g.noui))
    g.command(f"bossbar set {bossbar.bar(g)} players" + f" {g.who}" * (not g.noui))


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


CODES = {                                     # code -> the resources, the chat answer or a function
    "aegis": aegis,
    "black death": lambda g, player: [destroy(g, n) for n in others(g)],
    "cheese steak jimmy's": {"food": 10000},
    "going above and beyond": flag("beyond", "Technologies: up to 256 researches"),
    "i r winner": end("Victory", "gold"),
    "lumberjack": {"wood": 10000},
    "marco": "polo",                          # an easter egg (#1057)
    "my cpu can handle it": cpu,
    "natural wonders": wonders,
    "ninjaconnor": ALL,
    "ninjalui": ALL,
    "noui": noui,
    "polo": polo,
    "resign": lambda g, player: defeat(g, g.player),
    "robin hood": {"gold": 10000},
    "rock on": {"stone": 10000},
    "rowshep": ALL,
    "sharing is caring": flag("sharing", "Sharing is caring: your income goes to your allies"),
    "tech tech one two free": flag("free_techs", "Technologies are free"),
    "torpedo1": lambda g, player: destroy(g, 1),
    "torpedo2": lambda g, player: destroy(g, 2),
    "torpedo3": lambda g, player: destroy(g, 3),
    "torpedo4": lambda g, player: destroy(g, 4),
    "torpedo5": lambda g, player: destroy(g, 5),
    "torpedo6": lambda g, player: destroy(g, 6),
    "torpedo7": lambda g, player: destroy(g, 7),
    "torpedo8": lambda g, player: destroy(g, 8),
    "wimpywimpywimpy": lambda g, player: defeat(g, g.player) or g.ended and destroy(g, g.player),
    "woof woof": woof,
}
# The unit and transformation codes: one line per code in data/cheats.jsonl (#2034). A Transform has "units" (a list
# of unit names) or "rule" (the name of a function of this module).
CODES = dict(sorted((CODES | {r["name"]: Unit(r["unit"]) if "unit" in r else Transform(r["transform"], set(
    r["units"]).__contains__ if "units" in r else globals()[r["rule"]])
    for r in table.load("cheats.jsonl")}).items()))
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
    import gather                                                      # gather imports this module
    if not g.cheats or "passed" not in g.command(f"execute if entity {gather.only(g.who, f'scores={{{OBJECTIVE}=1..}}')}"):
        return []
    out = []
    for player in g.people():                                          # two people: only the own team (#1310)
        m = player and re.search(r" has (\d+) ", g.command(f"scoreboard players get {player} {OBJECTIVE}"))
        if m and 0 < int(m.group(1)) <= len(NAMES):
            g.command(f"scoreboard players reset {player} {OBJECTIVE}")
            out.append((player, NAMES[int(m.group(1)) - 1]))
            apply(g, *out[-1])
    return out
