"""A trigger with the condition "Object Attacked" fires in the converted world when its unit takes damage (#2779): the
tick function tests the HurtTime of the unit with the tag aoe2mc.r<ref> (#2617), 10 ticks after each hit."""
from collections import Counter

import aoe2mc
import triggers

CHAT = dict(type=aoe2mc.SEND_CHAT, message="We are attacked.", player=1, time=0, object=None, tile=[-1, -1],
            area=[-1] * 4)


def attacked(ref=5, unit=True):
    return dict(type=aoe2mc.OBJECT_ATTACKED, timer=0, inverted=False, ref=ref, unit=unit, player=2)


def files(conds, stats=None):
    trig = dict(id=3, name="t", enabled=True, looping=False, conditions=conds, effects=[CHAT])
    return aoe2mc.trigger_files([trig], stats=stats)[1]


def test_the_tick_function_tests_the_hurt_time_of_the_unit():
    assert files([attacked()])["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        "execute if entity @e[tag=aoe2mc.r5,nbt=!{HurtTime:0s}] unless score #3 aoe_trig matches 1 "
        "run function aoe2mc:trigger/3"]


def test_a_building_is_not_supported_yet():
    stats = Counter()
    assert "data/aoe2mc/function/tick.mcfunction" not in files([attacked(unit=False)], stats)
    assert stats["object condition (not an entity, not supported yet)"] == 1


def test_read_scenario_keeps_the_object_and_the_map_names_the_command():
    assert aoe2mc.OBJECT_ATTACKED in aoe2mc.OBJECT_TESTS           # read_scenario adds ref, unit and player
    assert "HurtTime" in triggers.MAP[("condition", "OBJECT_ATTACKED")]
    assert "#2779" in triggers.MAP[("condition", "OBJECT_ATTACKED")]
