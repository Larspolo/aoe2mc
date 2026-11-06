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
import lang
import savegame

CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> save\s*$")   # the chat word, as the server logs it


def save(game, out):
    """Write the world into a save folder and export it to out. Returns out."""
    game.command("save-off")
    game.command("save-all flush")
    try:
        folder = savegame.write(savegame.folder(game.world), game.world, None)
    finally:
        game.command("save-on")
    path = export.export(folder, out)
    game.command("tellraw @a " + json.dumps(lang.text("aoe2mc.editor.saved", os.path.abspath(path), color="green")))
    return path


def words(game, seen):
    """(the new log length, the count of `save` chat lines in the log after seen)."""
    log = game.server.log
    return len(log), sum(1 for line in log[seen:] if CHAT.search(line))


def run(game, out, alive):
    """Answer the chat word `save` while alive() (the console thread of run.main is alive)."""
    seen = len(game.server.log)
    while alive():
        seen, n = words(game, seen)
        if n:
            print(f"Saved the map: {save(game, out)}")
        time.sleep(0.5)
