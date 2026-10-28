"""Timer triggers freeze the units of a player in an area (#2608)."""
import numpy as np

import aoe2mc


def effect(area=(1, 2, 2, 3), player=1):
    return dict(type=aoe2mc.FREEZE_OBJECT, message="", player=player, time=0, object=None, tile=[-1, -1],
                area=list(area))


def lines(effects, T=4):
    trig = dict(id=7, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_freeze_sets_no_ai_on_the_units_in_the_area_and_their_mounts():
    sel = aoe2mc.area_selector(effect(), 4)
    assert "tag=aoe2mc.p1" in sel and "x=4," in sel
    assert lines([effect()]) == [f"execute as {sel} on vehicle run data merge entity @s {{NoAI:1b}}",
                                 f"execute as {sel} run data merge entity @s {{NoAI:1b}}"]


def test_gaia_units_have_the_gaia_tag():
    assert all("@e[tag=aoe2mc.p0," in line for line in lines([effect(player=0)]))   # #2916


def test_no_area_gives_no_line():
    assert lines([effect(area=(-1, -1, -1, -1))]) == []
