"""Triggers make the units of a player in an area invulnerable and vulnerable again (#2695): the tag Invulnerable of
the entity. Enable keeps the garrisoned units invulnerable (#807)."""
import numpy as np

import aoe2mc


def effect(type, area=(1, 2, 2, 3), player=1):
    return dict(type=type, message="", player=player, time=0, object=None, tile=[-1, -1], area=list(area))


def lines(effects, T=4):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_disable_makes_the_units_in_the_area_invulnerable():
    sel = aoe2mc.area_selector(effect(0), 4)
    assert lines([effect(aoe2mc.DISABLE_UNIT_ATTACKABLE)]) == \
        [f"execute as {sel} run data merge entity @s {{Invulnerable:1b}}"]


def test_enable_makes_them_vulnerable_again_but_not_the_garrisoned_units():
    sel = aoe2mc.area_selector(effect(0), 4)
    assert lines([effect(aoe2mc.ENABLE_UNIT_ATTACKABLE)]) == \
        [f"execute as {sel} unless entity @s[tag={aoe2mc.GARRISONED}] run data merge entity @s {{Invulnerable:0b}}"]


def test_no_area_gives_no_line():
    assert lines([effect(aoe2mc.DISABLE_UNIT_ATTACKABLE, area=(-1, -1, -1, -1))]) == []
