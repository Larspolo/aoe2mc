"""The start lines to the players (#5514): the goal, the first step and the controls; a tutorial gives only the controls."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402
from test_start_on_join import FakeGame, Side, join_after  # noqa: E402


def start(settings):
    game, now = FakeGame(), [0.0]
    game.settings = settings
    sleep = join_after(game, ["Steve"], now)
    run.start_on_join(game, [Side(lambda: now[0])], 1, sleep=lambda s: (game.command("sleep"), sleep(s)))
    return [json.loads(c[len("tellraw @a "):]) for c in game.sent if c.startswith("tellraw @a ") and "translate" in c]


def test_one_person_gets_three_lines():
    lines = start({"victory": "conquest"})
    assert [line["translate"] for line in lines] == ["aoe2mc.run.welcome_goal", "aoe2mc.run.welcome_first",
                                                    "aoe2mc.run.welcome_controls"]
    assert lines[0]["with"] == ["conquest"]
    assert lines[2]["click_event"] == {"action": "run_command", "command": "/controls"}


def test_tutorial_gets_only_the_controls():
    lines = start({"tutorial": True})
    assert [line["translate"] for line in lines] == ["aoe2mc.run.welcome_controls"]
    assert lines[0]["click_event"]["command"] == "/controls"
