"""The tick triggers wait for the start of the game (#3892): /tick freeze does not stop the tick function."""
import os
import sys

import scenarios

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game")]
import run  # noqa: E402
from test_start_on_join import FakeGame, Side  # noqa: E402


def test_the_tick_tag_runs_the_triggers_only_without_wait(tmp_path):
    texts = aoe2mc.read_scenario(scenarios.triggers(str(tmp_path / "t.aoe2scenario")))[4]
    load, files = aoe2mc.trigger_files(texts["triggers"], T=4)
    assert files["data/minecraft/tags/function/tick.json"] == {"values": ["aoe2mc:tick_wait"]}
    assert files["data/aoe2mc/function/tick_wait.mcfunction"].splitlines() == [
        "execute unless score #wait aoe_trig matches 1 run function aoe2mc:tick"]
    assert not any("#wait" in x for x in load)                       # a world without the game program runs them


def test_the_start_resets_wait_before_the_unfreeze():
    game = FakeGame()
    game.joined = {"Steve"}
    run.start_on_join(game, [Side(lambda: 0.0)], 1, sleep=lambda s: None)
    assert game.sent[-2:] == ["scoreboard players reset #wait aoe_trig", "tick unfreeze"]   # after the countdown (#5506)
