"""A trigger effect with selected objects acts on these objects, plus the units of its area (#2975)."""
import numpy as np

import aoe2mc

NONE = [-1, -1, -1, -1]


def effect(kind, selected=(), area=NONE, player=2, **keys):
    return dict(dict(type=kind, message="", player=player, time=0, object=None, tile=[-1, -1], area=list(area),
                     selected=list(selected)), **keys)


def lines(effects, T=4):
    trig = dict(id=7, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=5, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def all_of_player_2(out):
    return [line for line in out if "@e[tag=aoe2mc.p2,tag=!aoe2mc.mount]" in line]


def test_kill_ownership_and_damage_act_only_on_the_selected_archers():
    out = lines([effect(aoe2mc.KILL_OBJECT, [10]),
                 effect(aoe2mc.CHANGE_OWNERSHIP, [11], target=1),
                 effect(aoe2mc.DAMAGE_OBJECT, [11], quantity=5)])
    assert not all_of_player_2(out), out
    assert "kill @e[tag=aoe2mc.p2,tag=aoe2mc.r10]" in out
    assert "tag @e[tag=aoe2mc.p2,tag=aoe2mc.r11] add aoe2mc.own" in out
    assert "execute as @e[tag=aoe2mc.p2,tag=aoe2mc.r11] run damage @s 5" in out


def test_teleport_task_and_freeze_need_no_area_with_a_selection():
    at = "@e[tag=aoe2mc.p2,tag=aoe2mc.r10]"
    assert f"tp {at} 6.5 70 6.5" in lines([effect(aoe2mc.TELEPORT_OBJECT, [10], tile=[1, 1])])
    assert f"tag {at} add aoe_task7_0" in lines([effect(aoe2mc.TASK_OBJECT, [10], tile=[1, 1])])
    assert f"execute as {at} run data merge entity @s {{NoAI:1b}}" in lines([effect(aoe2mc.FREEZE_OBJECT, [10])])


def test_two_selected_units_get_a_temporary_tag():
    out = lines([effect(aoe2mc.FREEZE_OBJECT, [10, 11])])
    assert out[:2] == ["tag @e[tag=aoe2mc.p2,tag=aoe2mc.r10] add aoe2mc.sel",
                       "tag @e[tag=aoe2mc.p2,tag=aoe2mc.r11] add aoe2mc.sel"]
    assert "execute as @e[tag=aoe2mc.sel] run data merge entity @s {NoAI:1b}" in out
    assert out[-1] == "tag @e[tag=aoe2mc.sel] remove aoe2mc.sel" and not all_of_player_2(out)


def test_a_selection_and_an_area_act_on_both():
    out = lines([effect(aoe2mc.FREEZE_OBJECT, [10], area=(1, 2, 2, 3))])
    area = aoe2mc.area_selector(dict(player=2, area=[1, 2, 2, 3]), 4)
    assert out[:2] == ["tag @e[tag=aoe2mc.p2,tag=aoe2mc.r10] add aoe2mc.sel", f"tag {area} add aoe2mc.sel"]
    assert "execute as @e[tag=aoe2mc.sel] run data merge entity @s {NoAI:1b}" in out


def test_kill_of_a_selected_knight_also_kills_its_horse():
    out = lines([effect(aoe2mc.KILL_OBJECT, [10], object=("U", "KNIGHT"))])
    at = next(line[5:] for line in out if line.startswith("kill "))
    assert "tag=aoe2mc.r10" in at and f"execute as {at} on vehicle run kill @s" in out


def test_kill_with_no_type_also_kills_the_mounts():
    out = lines([effect(aoe2mc.KILL_OBJECT)])
    assert out[:2] == ["execute as @e[tag=aoe2mc.p2,tag=!aoe2mc.mount] on vehicle run kill @s",
                       "kill @e[tag=aoe2mc.p2,tag=!aoe2mc.mount]"]


def test_remove_object_of_a_selected_unit_needs_no_area():
    out = lines([effect(aoe2mc.REMOVE_OBJECT, [10])])
    assert out == ["execute as @e[tag=aoe2mc.p2,tag=aoe2mc.r10] on vehicle run kill @s",
                   "kill @e[tag=aoe2mc.p2,tag=aoe2mc.r10]"]
