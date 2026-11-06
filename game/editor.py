"""The map editor mode of the game program (#5999, epic #5998).

    python3 game/run.py WORLD --editor OUT.aoe2scenario

The world starts with no game time: no play(), so no gather tick, no bot, no age, no victory and no fog. The units
and buildings stand still. The person paints the terrain with the creative inventory (run.py sets creative mode) and
places water. The chat word `save` and the stop of the server write a save folder (savegame.write, no game state)
and export it to OUT (export.export): export.ground() gives each painted tile the AoE2 terrain of its new top block.
Vanilla logs each chat line ("<name> text"), so the log of the server is enough: no plugin command.
"""
import json
import os
import re
import time

import export
import gather
import lang
import menu
import savegame

CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> save\s*$")   # the chat word, as the server logs it


class State:
    """The light state of the editor (#6012): no Gather, but what menu, build.free and build.found need: the map of
    aoe2mc.json, the open chest menus, command, and the list of placed objects (AoE2 unit ID, owner, tile)."""

    def __init__(self, game, data=None):
        if data is None:
            with open(os.path.join(game.world, "aoe2mc.json")) as f:
                data = json.load(f)
        self.game, self.data, self.map = game, data, gather.Map(data)
        self.menus, self.placed, self.person = {}, [], None

    def command(self, cmd):
        return self.game.command(cmd)

    def place(self, unit_id, player, tile):
        """Add an object to the save: tile (x, y) in the tiles of the world."""
        self.placed.append({"id": int(unit_id), "player": int(player), "tile": [float(v) for v in tile]})

    def dump(self):
        return {"placed": list(self.placed)}


def save(game, out, state=None):
    """Write the world and the placed objects of state into a save folder and export it to out. Returns out."""
    game.command("save-off")
    game.command("save-all flush")
    try:
        folder = savegame.write(savegame.folder(game.world), game.world, state.dump() if state else None)
    finally:
        game.command("save-on")
    path = export.export(folder, out, heights=True)
    game.command("tellraw @a " + json.dumps(lang.text("aoe2mc.editor.saved", os.path.abspath(path), color="green")))
    return path


def words(game, seen):
    """(the new log length, the count of `save` chat lines in the log after seen)."""
    log = game.server.log
    return len(log), sum(1 for line in log[seen:] if CHAT.search(line))


def tick(state):
    """One click tick: the clicks of the open menus reach their handlers."""
    return menu.clicks(state) if state.menus else []


def run(game, out, alive, state=None):
    """Answer the chat word `save` and the menu clicks while alive() (the console thread of run.main is alive)."""
    state = state or State(game)
    game.editor = state                                                # the save at the stop of run.main
    seen = len(game.server.log)
    while alive():
        tick(state)
        seen, n = words(game, seen)
        if n:
            print(f"Saved the map: {save(game, out, state)}")
        time.sleep(0.5)
