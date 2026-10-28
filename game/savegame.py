"""Save a game of the game program and load it again (epic #2253, #2255).

The Minecraft save keeps the blocks and the mobs (their UUIDs too): the server plays the world in place and writes it
when it stops, so a save is a copy of the world folder. The state of the program (`gather.Gather`) goes into
`savegame.json` next to it: the resources, the technologies (the age comes from them) and the population of each player,
the train and research queues, the construction sites (also the done ones: the buildings of the game) and the rally
points (#2257), and the orders of the units (#2258): the job, target and load of each villager, the farmers, stances,
control groups and garrisons. A villager keeps no path: after the load it walks again with Minecraft path finding (P2).
The save also keeps the wonder and relic victory timers and the market prices (#2324), the game settings of the
command line (`run.py` options, "settings"), the attack time and wave of the bot (#2325), and the relics and the monk
orders (#2412: `monk.relics`, the conversions and the rest of the monks).
"""
import json
import os
import shutil
import time

FILE = "savegame.json"
FIELDS = ("stock", "spare", "seconds", "repeats", "pop")              # dicts and numbers of Gather, as they are
PACKED = ("queues", "trained", "sites", "rally")                       # with tuples (a building rect, a cell): pack()
OPTIONAL = ("rates", "relic_timer", "wonder_shown", "wonders", "wonders_gone")   # only on a Gather that has them (#2324)
MONK = ("carrier_at", "converting", "faith", "fetching", "heal_time", "monk_at", "relic_gold", "relic_homes",
        "relic_time", "relics")                                        # game/monk.py: the relics and monk orders (#2412)
ROUTES = ("trade", "trebs")                                            # trade.py, trebuchet.py: as OPTIONAL (#2413)
JOB = ("state", "load", "res", "job", "lap", "prey")                  # fields of a gather.Villager, as they are
IDLE = ("to_rally", "to_repair", "repair")                             # orders that the save does not keep yet
BOT = ("time", "charged", "attack")                                    # fields of a bot.Bot, as they are (#2325)
SETTINGS = ("all_techs", "bot", "bot_attack", "cheats", "civ", "full_tech_tree", "people", "reveal", "teams", "victory")   # run.py options
SKIP = ("session.lock",)                                               # the lock of the running server


def sides(g):
    """The Gather of each player: the people (run.Side) and the bot (bot.Bot) keep theirs in .g."""
    return [g, *(s.g for s in getattr(g, "bots", ()) if hasattr(s, "g"))]


def pack(v):
    """v in a JSON form that unpack() turns back: a tuple and a dict with keys that are not text get a tag."""
    if isinstance(v, tuple):
        return {"tuple": [pack(x) for x in v]}
    if isinstance(v, (set, frozenset)):
        return {"set": sorted((pack(x) for x in v), key=repr)}
    if isinstance(v, dict) and not all(isinstance(k, str) for k in v):
        return {"items": sorted(([pack(k), pack(x)] for k, x in v.items()), key=repr)}
    if isinstance(v, dict):
        return {k: pack(x) for k, x in v.items()}
    return [pack(x) for x in v] if isinstance(v, list) else v


def unpack(v):
    if isinstance(v, dict) and set(v) == {"tuple"}:
        return tuple(unpack(x) for x in v["tuple"])
    if isinstance(v, dict) and set(v) == {"set"}:
        return {unpack(x) for x in v["set"]}
    if isinstance(v, dict) and set(v) == {"items"}:
        return {unpack(k): unpack(x) for k, x in v["items"]}
    if isinstance(v, dict):
        return {k: unpack(x) for k, x in v.items()}
    return [unpack(x) for x in v] if isinstance(v, list) else v


def dump(g):
    """The saved state of the game of g as a JSON dict (sorted keys and lists: the same game gives the same file).
    The settings of the game (run.main puts them on the server as .settings) go under "settings", the bot values under
    the player of the bot (#2325)."""
    d = {"players": {str(x.player): {**{f: getattr(x, f) for f in FIELDS}, "techs": sorted(x.techs),
                                     **{f: pack(getattr(x, f)) for f in PACKED}, **orders(x),
                                     **{f: pack(vars(x)[f]) for f in OPTIONAL + MONK + ROUTES if f in vars(x)}}
                    for x in sides(g)}}
    for b in bots(g):
        d["players"][str(b.g.player)]["bot"] = {f: getattr(b, f) for f in BOT}
    if getattr(g.game, "settings", None):
        d["settings"] = dict(g.game.settings)
    return d


def bots(g):
    """The bots (bot.Bot) of g: Gather.bots also holds the Sides of the people."""
    return [b for b in getattr(g, "bots", ()) if hasattr(b, "charged")]


def orders(x):
    """The orders of the units of the Gather x (#2258): JSON has no tuple keys, so the tile and footprint keys go into
    sorted [key, value] lists."""
    return {"villagers": {u: {**{f: getattr(v, f) for f in JOB}, "pos": list(v.pos), "tree": v.tree and list(v.tree),
                              "site": v.site and list(v.site["footprint"])} for u, v in sorted(x.villagers.items())},
            "farmers": sorted([list(t), u] for t, u in x.farmers.items()),
            "stances": dict(sorted(x.stances.items())),
            "groups": {str(n): sorted(us) for n, us in sorted(x.groups.items())},
            "garrisons": sorted([list(r), list(us)] for r, us in x.garrisons.items()),
            "ships": {u: {**{f: getattr(v, f) for f in JOB}, "pos": list(v.pos), "tree": v.tree and list(v.tree),
                          "site": v.site and list(v.site["footprint"]), "goal": v.path and list(v.path[-1]),
                          **({"route": pack(v.route)} if hasattr(v, "route") else {})}
                      for u, v in sorted(getattr(x, "ships", {}).items())}}


def sail_again(x, p):
    """Put the saved ship orders of p (orders) on the Gather x (#2413): a ship with a goal sails to it again on a new
    water path (fleet.sail_to); a warship chases its prey and a fishing ship fishes on in fleet.tick. Then the trade
    carts walk on with the leg of their route (trade.leg) and a walking trebuchet walks on to its target (Minecraft
    path finding, P2)."""
    import fleet
    import gather
    import trade
    import trebuchet
    for u, s in p.get("ships", {}).items():                           # a save from before #2413 has no ships
        v = x.ships.setdefault(u, gather.Villager(u, tuple(s["pos"])))
        for f in JOB:
            setattr(v, f, s[f])
        v.pos, v.tree, v.path = tuple(s["pos"]), s["tree"] and tuple(s["tree"]), []
        v.site = next((t for t in x.sites if list(t["footprint"]) == s["site"]), None)
        if "route" in s:
            v.route = unpack(s["route"])
        if s["goal"]:
            fleet.sail_to(x, v, v.state, {tuple(s["goal"])})
    for u, t in sorted(getattr(x, "trade", {}).items()):
        if t.get("legs"):
            trade.leg(x, u, t["legs"][0])
    for u, (st, _, then) in sorted(vars(x).get("trebs", {}).items()):
        if st == "walking":
            trebuchet.walk(x, u, *then)


def give_orders(x, p):
    """Put the saved orders p (orders) on the Gather x. A villager that x does not know (trained in the game) comes
    back; a walking one walks again to its tree, drop site or construction site."""
    import gather
    x.farmers = {tuple(t): u for t, u in p["farmers"]}
    x.stances, x.groups = dict(p["stances"]), {int(n): set(us) for n, us in p["groups"].items()}
    x.garrisons = {tuple(r): list(us) for r, us in p["garrisons"]}
    for u, s in p["villagers"].items():
        v = x.villagers.setdefault(u, gather.Villager(u, tuple(s["pos"])))
        for f in JOB:
            setattr(v, f, s[f])
        v.pos, v.tree, v.path = tuple(s["pos"]), s["tree"] and tuple(s["tree"]), []
        v.site = next((t for t in x.sites if list(t["footprint"]) == s["site"]), None)   # the sites of the save (#2257)
        if v.state in IDLE or v.state in ("to_site", "build") and v.site is None:
            v.state = "idle"
        elif v.state == "to_site":
            x.build(v.site, {u})
        elif v.state == "to_tree":
            x.go(v, "to_tree", x.goals(v.tree))
        elif v.state == "to_drop":
            x.go(v, "to_drop", x.drop_goals(v))
        elif v.state == "to_prey":
            v.state = "hunt"                                           # the hunter follows its animal (Gather.strike)
    sail_again(x, p)


def load(g, d):
    """Put the saved state d (dump) on the Gather of each player that it names, and show the resources again."""
    import gather
    import train
    for x in sides(g):
        p = d["players"].get(str(x.player))
        if p is None:
            continue
        for f in FIELDS:
            setattr(x, f, type(getattr(x, f))(p[f]))
        x.techs = set(p["techs"])
        for f in PACKED + OPTIONAL + MONK + ROUTES:                             # the next tick shows the boss bars again
            if f in p:                                                 # a save before #2257 has no queues
                setattr(x, f, unpack(p[f]))
        if "villagers" in p:                                           # a save from before #2258 has no orders
            give_orders(x, p)
        for r in gather.RESOURCES:                                     # the sidebar of the resources (Gather.setup)
            x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
        train.sidebar(x)
    for b in bots(g):                                                  # its attack time and wave go on (#2325)
        for f, v in d["players"].get(str(b.g.player), {}).get("bot", {}).items():
            setattr(b, f, v)


def settings(a, d, given=()):
    """Put the settings of the saved state d on the run.py options a, except the options in given (the player gave
    them with --load: they win). A save before #2325 has no settings: a keeps the options of the command line.
    A given --bot-attack also wins over the saved attack time of the bot."""
    for k, v in d.get("settings", {}).items():
        if k in SETTINGS and k not in given:
            setattr(a, k, v)
    if "bot_attack" in given:
        for p in d["players"].values():
            p.get("bot", {}).pop("attack", None)


def folder(world):
    """The folder of the saves of world: saves/ next to it."""
    return os.path.join(os.path.dirname(os.path.abspath(world)), "saves")


def save(g, player):
    """Save the running game (the button "Save" of the Game menu, #2259): the world after `save-all flush`, with no
    autosave while it copies, and the state of all players (the Gather of run.play, also for a click of another
    person). The chat line of player names the save. Returns its path."""
    game = g.game
    game.command("save-off")
    game.command("save-all flush")
    try:
        path = write(folder(game.world), game.world, dump(getattr(game, "g", None) or g))
    finally:
        game.command("save-on")
    g.command(f"tellraw {player} " + json.dumps({"text": f"Saved the game: {os.path.basename(path)}", "color": "green"}))
    return path


def write(saves, world, state):
    """Copy the world and the state (dump) into a new folder under saves. Returns its path."""
    path = os.path.join(saves, f"{os.path.basename(os.path.normpath(world))}-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copytree(world, os.path.join(path, "world"), ignore=lambda d, names: [n for n in names if n in SKIP])
    with open(os.path.join(path, FILE), "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    return path


def read(path):
    """The state (dump) of the save folder path."""
    with open(os.path.join(path, FILE)) as f:
        return json.load(f)
