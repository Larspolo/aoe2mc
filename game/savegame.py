"""Save a game of the game program and load it again (epic #2253, #2255).

The Minecraft save keeps the blocks and the mobs (their UUIDs too): the server plays the world in place and writes it
when it stops, so a save is a copy of the world folder. The state of the program (`gather.Gather`) goes into
`savegame.json` next to it: the resources, the technologies (the age comes from them) and the population of each player.
"""
import json
import os
import shutil
import time

FILE = "savegame.json"
FIELDS = ("stock", "spare", "seconds", "repeats", "pop")              # dicts and numbers of Gather, as they are
SKIP = ("session.lock",)                                               # the lock of the running server


def sides(g):
    """The Gather of each player: the people (run.Side) and the bot (bot.Bot) keep theirs in .g."""
    return [g, *(s.g for s in getattr(g, "bots", ()) if hasattr(s, "g"))]


def dump(g):
    """The saved state of the game of g as a JSON dict (sorted keys and lists: the same game gives the same file)."""
    return {"players": {str(x.player): {**{f: getattr(x, f) for f in FIELDS}, "techs": sorted(x.techs)}
                        for x in sides(g)}}


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
        for r in gather.RESOURCES:                                     # the sidebar of the resources (Gather.setup)
            x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
        train.sidebar(x)


def write(folder, world, state):
    """Copy the stopped world and the state (dump) into a new folder under folder. Returns its path."""
    path = os.path.join(folder, f"{os.path.basename(os.path.normpath(world))}-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copytree(world, os.path.join(path, "world"), ignore=lambda d, names: [n for n in names if n in SKIP])
    with open(os.path.join(path, FILE), "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    return path


def read(path):
    """The state (dump) of the save folder path."""
    with open(os.path.join(path, FILE)) as f:
        return json.load(f)
