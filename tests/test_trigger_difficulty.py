"""#2704 (epic #2538): a trigger with the condition "Difficulty Level" fires when the game program runs the scenario at
that difficulty. The tick function tests the score #level of aoe_difficulty; the scenario mode sets it from the setting
"AI difficulty" (run.py --ai-difficulty)."""
import os
import sys

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

HARD = 1                                                               # DifficultyLevel.HARD of AoE2ScenarioParser


def files(level=HARD, looping=False):
    t = dict(id=4, name="t", enabled=True, looping=looping,
             conditions=[dict(type=aoe2mc.DIFFICULTY_LEVEL, timer=0, inverted=False, quantity=level)],
             effects=[dict(type=aoe2mc.SEND_CHAT, message="Hard", player=1, time=0, object=None, tile=[-1, -1],
                           area=[-1] * 4)])
    return aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16))


def test_the_tick_function_tests_the_score_of_the_difficulty():
    load, out = files()
    tick = out["data/aoe2mc/function/tick.mcfunction"]
    assert "execute if score #level aoe_difficulty matches 1 unless score #4 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/4" in tick
    assert "scoreboard objectives add aoe_difficulty dummy" in load
    assert 'tellraw @a {"text": "Hard"}' in out["data/aoe2mc/function/trigger/4.mcfunction"]


def test_the_extreme_difficulty_is_a_negative_score():
    tick = files(level=-1)[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "if score #level aoe_difficulty matches -1 " in tick


def test_the_scenario_mode_sets_the_score_from_the_ai_difficulty():
    server, g, _ = game({"0": {}, "1": {"color": "blue"}, "2": {"color": "red"}})
    g.game.settings = {"ai_difficulty": "hard"}
    scenario.setup(g, "scenario")
    assert "scoreboard players set #level aoe_difficulty 1" in server.log


def test_with_no_settings_the_difficulty_is_standard():
    server, g, _ = game({"0": {}, "1": {"color": "blue"}, "2": {"color": "red"}})
    assert not hasattr(g.game, "settings")
    scenario.setup(g, "scenario")
    assert "scoreboard players set #level aoe_difficulty 3" in server.log
