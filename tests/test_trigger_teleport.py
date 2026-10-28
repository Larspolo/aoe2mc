"""Timer triggers teleport the units of a player in an area to a tile (#2569)."""
import numpy as np

import aoe2mc


def effect(tile=(3, 5), area=(1, 2, 2, 3), player=1):
    return dict(type=aoe2mc.TELEPORT_OBJECT, message="", player=player, time=0, object=None, tile=list(tile),
                area=list(area))


def lines(effects, T=4):
    trig = dict(id=7, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_teleport_moves_the_units_in_the_area_to_the_middle_of_the_tile():
    sel = f"@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=4,y={aoe2mc.MIN_Y},z=8,dx=7,dy={aoe2mc.HEIGHT - 1},dz=7]"
    assert sel == aoe2mc.area_selector(effect(), 4)
    assert lines([effect()]) == [f"execute as {sel} on vehicle run tp @s 14.5 70 22.5",   # a rider with its horse
                                 f"tp {sel} 14.5 70 22.5"]


def test_gaia_units_have_the_gaia_tag():
    assert all("@e[tag=aoe2mc.p0," in line for line in lines([effect(player=0)]))   # #2916


def test_no_target_tile_or_area_gives_no_line():
    for e in (effect(tile=(-1, -1)), effect(area=(-1, -1, -1, -1)), effect(tile=(40, 5))):
        assert lines([e]) == []
