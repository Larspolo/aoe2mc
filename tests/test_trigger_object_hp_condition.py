"""#2701 (epic #2538): a trigger with the condition "Object HP" fires when the Health of one scenario object (its tag
aoe2mc.r<ref>, #2617) compares with a value. The tick function stores the Health in a score and tests it; a dead
object has no entity, so its score is reset and the trigger does not fire."""
import numpy as np

import aoe2mc

LESS = 1                                                               # Comparison.LESS of AoE2ScenarioParser


def files(ref=7, quantity=20, comparison=LESS, looping=False):
    t = dict(id=4, name="t", enabled=True, looping=looping,
             conditions=[dict(type=aoe2mc.OBJECT_HP, timer=0, inverted=False, ref=ref, quantity=quantity,
                              comparison=comparison)],
             effects=[dict(type=aoe2mc.SEND_CHAT, message="Hurt", player=1, time=0, object=None, tile=[-1, -1],
                           area=[-1] * 4)])
    return aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16))


def test_the_tick_function_stores_the_health_of_the_object():
    tick = files()[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "execute as @e[tag=aoe2mc.r7,limit=1] unless predicate aoe2mc:rider store result score #4.0 aoe_trig " \
           "run data get entity @s Health" in tick                    # a rider: its mount (#2976)


def test_the_trigger_fires_when_the_health_is_less_than_the_quantity():
    tick = files()[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "execute if score #4.0 aoe_trig matches ..19 unless score #4 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/4" in tick


def test_a_dead_object_does_not_fire_the_trigger():
    # the score of the last tick must not stay: it is reset before the store, which needs the entity (no entity: no score)
    tick = files()[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()
    reset = tick.index("scoreboard players reset #4.0 aoe_trig")
    store = next(i for i, line in enumerate(tick) if "store result score #4.0" in line)
    test = next(i for i, line in enumerate(tick) if "if score #4.0 aoe_trig matches" in line)
    assert reset < store < test


def test_the_comparison_sets_the_range_of_the_score():
    tick = files(quantity=20, comparison=0)[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "if score #4.0 aoe_trig matches 20 " in tick


def test_an_object_without_a_reference_is_not_converted():
    load, out = files(ref=-1)
    assert "data/aoe2mc/function/tick.mcfunction" not in out
