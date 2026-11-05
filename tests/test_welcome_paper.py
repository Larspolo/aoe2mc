"""The first step line says "left click" on Paper (#5859); vanilla keeps the right click."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402
from test_start_on_join import FakeGame, Side, join_after  # noqa: E402


def start(kind):
    game, now = FakeGame(), [0.0]
    game.settings = {"victory": "conquest"}
    game.kind = kind
    sleep = join_after(game, ["Steve"], now)
    run.start_on_join(game, [Side(lambda: now[0])], 1, sleep=lambda s: (game.command("sleep"), sleep(s)))
    return [json.loads(c[len("tellraw @a "):]) for c in game.sent if c.startswith("tellraw @a ") and "translate" in c]


def test_paper_first_step_says_left_click():
    line = start("paper")[1]
    assert line["translate"] == "aoe2mc.run.welcome_first_paper"


def test_vanilla_first_step_keeps_right_click():
    line = start("vanilla")[1]
    assert line["translate"] == "aoe2mc.run.welcome_first"
