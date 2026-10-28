"""Save a game of the game program and load it again (epic #2253, #2255).

The Minecraft save keeps the blocks and the mobs (their UUIDs too): the server plays the world in place and writes it
when it stops, so a save is a copy of the world folder. The state of the program (`gather.Gather`) goes into
`savegame.json` next to it: the resources, the technologies (the age comes from them) and the population of each player,
the train and research queues, the construction sites (also the done ones: the buildings of the game) and the rally
points (#2257).
"""
import json
import os
import shutil
import time

FILE = "savegame.json"
FIELDS = ("stock", "spare", "seconds", "repeats", "pop")              # dicts and numbers of Gather, as they are
PACKED = ("queues", "trained", "sites", "rally")                       # with tuples (a building rect, a cell): pack()
SKIP = ("session.lock",)                                               # the lock of the running server


def sides(g):
    """The Gather of each player: the people (run.Side) and the bot (bot.Bot) keep theirs in .g."""
    return [g, *(s.g for s in getattr(g, "bots", ()) if hasattr(s, "g"))]


def pack(v):
    """v in a JSON form that unpack() turns back: a tuple and a dict with keys that are not text get a tag."""
    if isinstance(v, tuple):
        return {"tuple": [pack(x) for x in v]}
    if isinstance(v, dict) and not all(isinstance(k, str) for k in v):
        return {"items": sorted(([pack(k), pack(x)] for k, x in v.items()), key=repr)}
    if isinstance(v, dict):
        return {k: pack(x) for k, x in v.items()}
    return [pack(x) for x in v] if isinstance(v, list) else v


def unpack(v):
    if isinstance(v, dict) and set(v) == {"tuple"}:
        return tuple(unpack(x) for x in v["tuple"])
    if isinstance(v, dict) and set(v) == {"items"}:
        return {unpack(k): unpack(x) for k, x in v["items"]}
    if isinstance(v, dict):
        return {k: unpack(x) for k, x in v.items()}
    return [unpack(x) for x in v] if isinstance(v, list) else v


def dump(g):
    """The saved state of the game of g as a JSON dict (sorted keys and lists: the same game gives the same file)."""
    return {"players": {str(x.player): {**{f: getattr(x, f) for f in FIELDS}, "techs": sorted(x.techs),
                                        **{f: pack(getattr(x, f)) for f in PACKED}} for x in sides(g)}}


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
        for f in PACKED:
            if f in p:                                                 # a save before #2257 has no queues
                setattr(x, f, unpack(p[f]))
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
