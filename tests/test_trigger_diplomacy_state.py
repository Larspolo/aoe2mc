"""#2757 (epic #2538): a trigger with the condition "Diplomacy State" fires when player A has the given stance to
player B. The tick function tests the score #p<A>.p<B> of aoe_dipstate (the stance + 1); the scenario mode sets it at
the start from the teams and the "neutral" lists of aoe2mc.json, and again after each "Change Diplomacy"."""
import os
import sys

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_diplomacy import Game  # noqa: E402
from test_scenario_mode import game  # noqa: E402

ENEMY = 3                                                              # DiplomacyState.ENEMY of AoE2ScenarioParser


def files(a=1, b=2, stance=ENEMY):
    t = dict(id=6, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.DIPLOMACY_STATE, timer=0, inverted=False, player=a, target=b,
                              diplomacy=stance)],
             effects=[dict(type=aoe2mc.SEND_CHAT, message="War", player=1, time=0, object=None, tile=[-1, -1],
                           area=[-1] * 4)])
    return aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16))


def test_the_tick_function_tests_the_score_of_the_stance():
    tick = files()[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "execute if score #p1.p2 aoe_dipstate matches 4 unless score #6 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/6" in tick


def test_ally_is_score_1():
    assert "if score #p2.p3 aoe_dipstate matches 1 " in files(2, 3, 0)[1]["data/aoe2mc/function/tick.mcfunction"]


def test_the_scenario_mode_sets_the_stances_at_the_start():
    server, g, _ = game({"0": {}, "1": {"team": 1}, "2": {"team": 1}, "3": {"team": 2, "neutral": [1]}})
    scenario.setup(g, "scenario")
    assert "scoreboard objectives add aoe_dipstate dummy" in server.log
    for line in ("#p1.p2 aoe_dipstate 1", "#p2.p1 aoe_dipstate 1", "#p1.p3 aoe_dipstate 4", "#p3.p1 aoe_dipstate 2",
                 "#p3.p2 aoe_dipstate 4"):
        assert f"scoreboard players set {line}" in server.log
    assert not [c for c in server.log if "aoe_dipstate" in c and ("#p0." in c or ".p0 " in c or "#p1.p1 " in c)]


def test_a_change_to_ally_sets_the_state_score():
    g = Game({"0": {}, "1": {}, "2": {}}, {"#any": 1, "#p1.p2": 1})
    scenario.diplomacy(g)
    assert "scoreboard players set #p1.p2 aoe_dipstate 1" in g.log
    assert "scoreboard players set #p2.p1 aoe_dipstate 1" in g.log
