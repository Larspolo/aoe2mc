"""A trigger made in the editor on a real server runs in the game program after the conversion of the save (#6092):
"Timer 2 s, then Send Chat", and "Timer 2 s, then Kill Object" with the object selected by a look."""
import contextlib
import io
import os
import shutil
import sys

import pytest
from test_mc_check import mojang_reachable

import aoe2mc
from tools import scenarios

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
TEXT = "Made in the editor"
ARCHERS = "@e[type=minecraft:skeleton,tag=aoe2mc.p1]"


@pytest.mark.mc
def test_an_editor_trigger_runs_after_the_conversion(tmp_path):
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import editor
    import mc_shot
    from test_editor_palette import eye_over, free_cells
    from test_editor_trigger_fields import add
    from test_editor_trigger_types import opened
    from test_triggers_server import count, datapack_problems, wait

    from game import run
    world, out = str(tmp_path / "W"), str(tmp_path / "OUT.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")), world)
    with run.Game(world) as game:
        game.forceload()
        s = editor.State(game)
        opened(s)
        add(s, 0, "condition", "TIMER").timer = 2
        add(s, 0, "effect", "SEND_CHAT").message = TEXT
        placed = editor.place_at(s, 1, "ARCHER", free_cells(s, 1)[0])
        at, _ = opened(s)
        add(s, at, "condition", "TIMER").timer = 2
        kill = add(s, at, "effect", "KILL_OBJECT")
        editor.fields_menu(s, "p", at, 1)
        s.menus["p"]("p", editor.LOOK, False, right=False)
        cell = tuple(placed["rect"][::2])
        assert [editor.here(s, "p", *eye_over(s, cell)) for _ in (0, 1)][-1] or kill.selected_object_ids
        assert kill.selected_object_ids == [placed["ref"]]
        with contextlib.redirect_stdout(io.StringIO()):
            editor.save(game, out, s)
    w2 = str(tmp_path / "W2")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, w2)
    with run.Game(w2) as game, mc_shot.Client(game.game_port, game.version) as client:
        game.command("tick freeze")                                    # the timers wait until the client is there
        game.forceload()
        assert wait(lambda: count(game, ARCHERS) > 0, 20)
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        archers = count(game, ARCHERS)
        game.command("tick unfreeze")
        assert wait(lambda: "[CHAT] " + TEXT in client.text(), 20), client.text()[-2000:]
        assert wait(lambda: count(game, ARCHERS) == archers - 1, 15)
        assert datapack_problems(game.server.log) == []
