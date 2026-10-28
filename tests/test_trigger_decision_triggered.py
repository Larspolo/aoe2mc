"""#2888 (epic #2538): the trigger condition "Decision Triggered". It fires when the last click on an option of
"Create Decision" (#2886: #last of aoe_decision, decision ID × 10 + option) is the named option."""
import numpy as np

import aoe2mc


def condition(decision=2, option=1, inverted=False):
    return dict(type=aoe2mc.DECISION_TRIGGERED, timer=0, inverted=inverted, decision=decision, option=option)


def convert(*conditions):
    trig = dict(id=8, name="t", enabled=True, looping=False, conditions=list(conditions),
                effects=[dict(type=aoe2mc.SEND_CHAT, message="The king thanks you.", player=1, time=0, object=None,
                              tile=[-1, -1], area=[-1] * 4)])
    return aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16))


def test_the_tick_function_tests_the_last_click():
    load, files = convert(condition())
    tick = files["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert "execute if score #last aoe_decision matches 21 unless score #8 aoe_trig matches 1 run function " \
        "aoe2mc:trigger/8" in tick
    assert "scoreboard objectives add aoe_decision trigger" in load   # also with no "Create Decision"


def test_an_inverted_condition_fires_on_another_click():
    tick = convert(condition(option=2, inverted=True))[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "execute unless score #last aoe_decision matches 22 " in tick


def test_a_wrong_option_or_no_decision_gives_no_trigger():
    for c in (condition(option=0), condition(decision=-1)):
        assert "data/aoe2mc/function/trigger/8.mcfunction" not in convert(c)[1]
