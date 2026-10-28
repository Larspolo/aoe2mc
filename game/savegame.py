"""Save a game of the game program and load it again (epic #2253, #2255).

The Minecraft save keeps the blocks and the mobs (their UUIDs too): the server plays the world in place and writes it
when it stops, so a save is a copy of the world folder. The state of the program (`gather.Gather`) goes into
`savegame.json` next to it: the resources, the technologies (the age comes from them) and the population of each player,
and the orders of the units (#2258): the job, target and load of each villager, the farmers, stances, control groups
and garrisons. A villager keeps no path: after the load it walks again with Minecraft path finding (P2).
"""
import json
import os
import shutil
import time

FILE = "savegame.json"
FIELDS = ("stock", "spare", "seconds", "repeats", "pop")              # dicts and numbers of Gather, as they are
JOB = ("state", "load", "res", "job", "lap", "prey")                  # fields of a gather.Villager, as they are
IDLE = ("to_rally", "to_repair", "repair")                             # orders that the save does not keep yet
SKIP = ("session.lock",)                                               # the lock of the running server


def sides(g):
    """The Gather of each player: the people (run.Side) and the bot (bot.Bot) keep theirs in .g."""
    return [g, *(s.g for s in getattr(g, "bots", ()) if hasattr(s, "g"))]


def dump(g):
    """The saved state of the game of g as a JSON dict (sorted keys and lists: the same game gives the same file)."""
    return {"players": {str(x.player): {**{f: getattr(x, f) for f in FIELDS}, "techs": sorted(x.techs), **orders(x)}
                        for x in sides(g)}}


def orders(x):
    """The orders of the units of the Gather x (#2258): JSON has no tuple keys, so the tile and footprint keys go into
    sorted [key, value] lists."""
    return {"villagers": {u: {**{f: getattr(v, f) for f in JOB}, "pos": list(v.pos), "tree": v.tree and list(v.tree),
                              "site": v.site and list(v.site["footprint"])} for u, v in sorted(x.villagers.items())},
            "farmers": sorted([list(t), u] for t, u in x.farmers.items()),
            "stances": dict(sorted(x.stances.items())),
            "groups": {str(n): sorted(us) for n, us in sorted(x.groups.items())},
            "garrisons": sorted([list(r), list(us)] for r, us in x.garrisons.items())}


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
        v.site = next((t for t in x.sites if list(t["footprint"]) == s["site"]), None)   # the sites: #2257
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
        if "villagers" in p:                                           # a save from before #2258 has no orders
            give_orders(x, p)
        for r in gather.RESOURCES:                                     # the sidebar of the resources (Gather.setup)
            x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
        train.sidebar(x)


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
