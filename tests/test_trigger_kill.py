"""The trigger effect "Kill Object" kills the units of its player and type in its area (#2568), as "Remove Object"
(#656): the Minecraft kill shows the death of the unit, as the AoE2 death."""
from collections import Counter

import aoe2mc
from test_trigger_objects import effect, lines


def test_kill_object_kills_the_units_of_the_player_and_type_in_the_area():
    stats = Counter()
    kill, = lines([effect(aoe2mc.KILL_OBJECT, "ARCHER", player=1, area=(1, 2, 3, 2))], stats)
    assert kill == "kill @e[type=minecraft:skeleton,tag=aoe2mc.p1,tag=!aoe2mc.mount,x=4,y=-64,z=8,dx=11,dy=383,dz=3]"
    assert stats == Counter(kill=1)


def test_kill_object_with_no_area_kills_the_units_of_the_player_on_the_whole_map():
    kill, = lines([effect(aoe2mc.KILL_OBJECT, "ARCHER", player=2)])
    assert kill == "kill @e[type=minecraft:skeleton,tag=aoe2mc.p2,tag=!aoe2mc.mount]"
    any_unit, = lines([effect(aoe2mc.KILL_OBJECT, player=2)])
    assert any_unit == "kill @e[tag=aoe2mc.p2,tag=!aoe2mc.mount]"


def test_kill_object_of_a_rider_kills_its_mount_too():
    ride, kill = lines([effect(aoe2mc.KILL_OBJECT, "KNIGHT")])
    assert ride == "execute as @e[type=minecraft:zombie,tag=aoe2mc.p1,tag=!aoe2mc.mount] on vehicle run kill @s"
    assert kill == "kill @e[type=minecraft:zombie,tag=aoe2mc.p1,tag=!aoe2mc.mount]"


def test_kill_object_of_gaia_kills_the_gaia_units_and_never_a_player():
    stats = Counter()
    assert lines([effect(aoe2mc.KILL_OBJECT, player=0)], stats) == ["kill @e[tag=aoe2mc.p0,tag=!aoe2mc.mount]"]  # #2916
    assert stats == Counter({"kill": 1})
    assert lines([effect(aoe2mc.KILL_OBJECT, "DEER", kind="U", player=0)])[-1].startswith("kill @e[type=minecraft:")
    remove, = lines([effect(aoe2mc.REMOVE_OBJECT, player=0, area=(1, 1, 2, 2))])
    assert remove.startswith("kill @e[tag=aoe2mc.p0,tag=!aoe2mc.mount,x=4,")


def test_remove_object_with_no_area_does_nothing_as_before():
    assert lines([effect(aoe2mc.REMOVE_OBJECT, "ARCHER")]) == []
