"""The trigger effect "Change Object Name" renames the units of its player and type in its area (#2616)."""
from collections import Counter

import numpy as np

import aoe2mc


def effect(message, name="MILITIA", player=1, area=(2, 3, 4, 5)):
    return dict(type=aoe2mc.CHANGE_OBJECT_NAME, message=message, player=player, time=0,
                object=("U", name) if name else None, tile=[-1, -1], area=list(area))


def lines(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_change_object_name_sets_the_name_on_the_units_of_the_type_in_the_area():
    stats = Counter()
    line, = lines([effect("Sir William")], stats)
    assert line == ("execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t74,x=8,y=-64,z=12,dx=11,dy=383,"
                    'dz=11] run data modify entity @s CustomName.text set value "Sir William"')   # the color stays
    assert stats == Counter({"change object name": 1})


def test_the_color_tags_are_not_in_the_name():
    line, = lines([effect("<RED>Sir William")])
    assert line.endswith('set value "Sir William"') and "<RED>" not in line


def test_an_empty_name_gives_no_command():
    stats = Counter()
    assert lines([effect("<BLUE> ")], stats) == [] and stats == Counter({"change object name (no name)": 1})
