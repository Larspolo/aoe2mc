"""Live replay: a unit that dies leaves a short death mark (#846, Deaths.java of the plugin). Fake RCON and a real
Paper server."""
import os
import re
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def start(ai, bar=True):
    game = Fake()
    replay.Replay(game, data([{"time": 0, "player": 1, "kind": "chat", "text": "hi"}]), ai=ai).run(
        clock=lambda: 0.0, sleep=lambda s: None, log=None, bar=bar)
    return game.sent


def test_the_replay_turns_the_marks_on_on_paper():
    sent = start(ai=True)
    assert sent.count("aoe deathmarks on") == 1 and sent.index("aoe deathmarks on") < sent.index(
        next(c for c in sent if c.startswith("tellraw")))                # before the first event
    assert "aoe deathmarks on" not in start(ai=False)                   # vanilla has no plugin
    assert "aoe deathmarks on" not in start(ai=True, bar=False)         # the unit tests of the replay


@pytest.mark.mc
def test_a_tagged_unit_leaves_a_mark_for_5_seconds(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    marks = "execute if entity @e[type=text_display,tag=aoe2mc.deathmark]"
    with run.Game(world) as game:
        game.forceload()
        game.command("team add aoe_p1")
        game.command("team modify aoe_p1 color red")
        for i, tags in ((161, f'"{replay.COUNTED}"'), (162, '"aoe2mc.p1"')):   # 162: not counted, no mark
            game.command(f"summon minecraft:pillager 8 80 8 {{UUID:[I;0,0,0,{i}],NoAI:1b,Tags:[{tags}]}}")
            game.command(f"team join aoe_p1 00000000-0000-0000-0000-0000000000{i:02x}")
        game.command("kill 00000000-0000-0000-0000-0000000000a1")          # marks off: no mark
        assert "Death marks: on" in game.command("aoe deathmarks on")
        game.command("kill 00000000-0000-0000-0000-0000000000a2")
        assert "Count" not in game.command(marks) or re.search(r"Count: 0", game.command(marks))
        game.command("summon minecraft:pillager 8 80 8 {UUID:[I;0,0,0,163],NoAI:1b,Tags:[\"%s\"]}" % replay.COUNTED)
        game.command("team join aoe_p1 00000000-0000-0000-0000-0000000000a3")
        game.command("kill 00000000-0000-0000-0000-0000000000a3")
        assert re.search(r"Count: 1", game.command(marks))
        text = game.command("data get entity @e[type=text_display,tag=aoe2mc.deathmark,limit=1] text")
        assert "☠" in text and "red" in text
        time.sleep(6)
        assert not re.search(r"Count: [1-9]", game.command(marks))
