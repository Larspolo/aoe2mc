"""A trigger with the condition "Capture Object" fires in the converted world when its unit belongs to the player of the
condition (#2619): the tick function tests the tags aoe2mc.r<ref> (the unit, #2617) and aoe2mc.p<player> (its owner,
#2570)."""
from collections import Counter

import aoe2mc

CHAT = dict(type=aoe2mc.SEND_CHAT, message="It is ours.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)


def capture(ref=7, player=2):
    return dict(type=aoe2mc.CAPTURE_OBJECT, timer=0, inverted=False, ref=ref, unit=True, player=player)


def tick(conds):
    trig = dict(id=3, name="t", enabled=True, looping=False, conditions=conds, effects=[CHAT])
    return aoe2mc.trigger_files([trig])[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()


def test_the_tick_function_tests_the_unit_and_the_owner():
    assert tick([capture()]) == ["execute if entity @e[tag=aoe2mc.r7,tag=aoe2mc.p2] unless score #3 aoe_trig matches 1 "
                                 "run function aoe2mc:trigger/3"]


def test_the_player_of_the_condition_is_the_tag_of_the_owner():
    assert tick([capture(player=1)])[0].startswith("execute if entity @e[tag=aoe2mc.r7,tag=aoe2mc.p1] ")


def test_a_building_with_no_player_is_not_supported():     # a building with a player: its score (#2940)
    trig = dict(id=3, name="t", enabled=True, looping=False, conditions=[capture(player=-1) | dict(unit=False)],
                effects=[CHAT])
    files = aoe2mc.trigger_files([trig], stats=Counter())[1]
    assert "data/aoe2mc/function/tick.mcfunction" not in files
