"""A trigger effect with a unit type acts only on the units of that AoE2 type (#2978): the selector has the type tag
aoe2mc.t<ID>, not a Minecraft mob, so a crossbowman or a monk is not an archer or a wolf."""
from collections import Counter

import aoe2mc
from test_trigger_objects import effect, lines


def test_kill_object_selects_the_type_tag_of_the_archer():
    kill, = lines([effect(aoe2mc.KILL_OBJECT, "ARCHER", player=2)])
    assert kill == "kill @e[tag=aoe2mc.p2,tag=!aoe2mc.mount,tag=aoe2mc.t4]"


def test_kill_object_of_a_hero_kills_the_hero_and_its_horse():
    stats = Counter()
    ride, kill = lines([effect(aoe2mc.KILL_OBJECT, "RICHARD_THE_LIONHEART", kind="H", player=1)], stats)
    assert kill == "kill @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t160]"
    assert ride == "execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t160] on vehicle run kill @s"
    assert stats == Counter(kill=1)


def test_change_ownership_teleport_and_freeze_select_the_type_tag_of_the_monk():
    change = lines([dict(effect(aoe2mc.CHANGE_OWNERSHIP, "MONK", player=2, area=(0, 0, 9, 9)), target=1)])
    assert change[0] == "tag @e[tag=aoe2mc.p2,tag=!aoe2mc.mount,tag=aoe2mc.t125,x=0,y=-64,z=0,dx=39,dy=383,dz=39] add aoe2mc.own"
    teleport = lines([effect(aoe2mc.TELEPORT_OBJECT, "MONK", player=1, area=(0, 0, 9, 9), tile=(5, 5))])
    assert all("tag=aoe2mc.t125," in line for line in teleport) and len(teleport) == 2
    freeze = lines([effect(aoe2mc.FREEZE_OBJECT, "MONK", player=1, area=(0, 0, 9, 9))])
    assert freeze[0].startswith("execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t125,x=0,")


def test_effect_without_a_type_selects_all_units_of_the_player_as_before():
    assert lines([effect(aoe2mc.KILL_OBJECT, player=2)])[-1] == "kill @e[tag=aoe2mc.p2,tag=!aoe2mc.mount]"
