"""The map editor tells the chat words `palette` and `save` at its start (#6017, epic #5998)."""
import contextlib
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from test_editor import FakeGame  # noqa: E402


def test_the_editor_tells_the_chat_words_before_its_first_tick(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    game = FakeGame(world)
    calls = []

    def alive():                                  # true at the first call, false after it: one tick
        calls.append(1)
        return len(calls) < 2

    with contextlib.redirect_stdout(io.StringIO()):
        editor.run(game, str(tmp_path / "out.aoe2scenario"), alive)
    hints = [c for c in game.sent if c.startswith("tellraw @a") and "aoe2mc.editor.start" in c]
    assert len(hints) == 1
    assert game.sent.index(hints[0]) == 0         # the first command of the editor, before any tick
    assert len(calls) == 2
