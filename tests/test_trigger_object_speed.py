"""The trigger effect "Change Object Speed" sets the walk speed of the units of its player in the converted world
(#2694), with the rule of the game program (game/ai.py movement_speed)."""
import math
from collections import Counter

import numpy as np

import aoe2mc
from game import ai, gather


def effect(quantity, player=1, area=(2, 3, 4, 5)):
    return dict(type=aoe2mc.CHANGE_OBJECT_SPEED, message="", player=player, time=0, object=None,
                tile=[-1, -1], area=list(area), quantity=quantity)


def lines(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_change_object_speed_sets_the_movement_speed_of_the_units_in_the_area():
    stats = Counter()
    found = lines([effect(2)], stats)
    value = round(math.sqrt(2 * 4 * gather.NORMAL / ai.WALK), 4)
    assert found[1].endswith(f" run attribute @s minecraft:movement_speed base set {value}")
    assert found[1].startswith("execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,")
    assert stats == Counter({"change object speed": 1})


def test_a_speed_of_zero_or_no_area_is_not_supported():
    stats = Counter()
    assert lines([effect(0)], stats) == [] and lines([effect(2, area=(-1, -1, -1, -1))], stats) == []
    assert stats == Counter({"change object speed (not supported)": 2})
