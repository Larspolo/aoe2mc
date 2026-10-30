"""The trigger effects "Change Object Attack" and "Change Object Armor" with the operation "set" give the units of their
player in their area the new value (#2909): the modifiers of the earlier add and subtract effects go, then a base set."""
from collections import Counter

import numpy as np
from test_trigger_unit_values import unit_value

import aoe2mc

SET, ADD, SUBTRACT = 1, 2, 3
AT = "execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11]"


def effect(type_, quantity, operation, armour_class=4):
    return dict(type=type_, message="", player=1, time=0, object=None, tile=[-1, -1], area=[2, 3, 4, 5],
                quantity=quantity, operation=operation, armour_class=armour_class)


def trigger(id, effects, timer):
    return dict(id=id, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=timer, inverted=False)])


def lines(triggers, id, stats=None):
    files = aoe2mc.trigger_files(triggers, 4, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)[1]
    return [x for x in files.get(f"data/aoe2mc/function/trigger/{id}.mcfunction", "").splitlines() if not unit_value(x)]


def test_a_set_of_the_attack_removes_the_earlier_modifiers_then_sets_the_base():
    stats = Counter()
    earlier = trigger(3, [effect(aoe2mc.CHANGE_OBJECT_ARMOR, 1, ADD),             # another kind: stays
                          effect(aoe2mc.CHANGE_OBJECT_ATTACK, 2, ADD)], 10)
    later = trigger(5, [effect(aoe2mc.CHANGE_OBJECT_ATTACK, 1, SUBTRACT, armour_class=3),
                        effect(aoe2mc.CHANGE_OBJECT_ATTACK, 7, SET)], 60)
    assert lines([earlier, later], 5, stats)[1:] == [
        f"{AT} run attribute @s minecraft:attack_damage modifier remove aoe2mc:trig_3_1",
        f"{AT} run attribute @s minecraft:attack_damage modifier remove aoe2mc:trig_5_0",
        f"{AT} run attribute @s minecraft:attack_damage base set 7"]
    assert stats["change object attack"] == 3


def test_a_set_of_the_armor_also_removes_the_modifiers_of_modify_object_attribute():
    attribute = dict(effect(aoe2mc.MODIFY_OBJECT_ATTRIBUTE, 0, ADD), attribute=8, aa=2)
    triggers = [trigger(3, [effect(aoe2mc.CHANGE_OBJECT_ARMOR, 1, SUBTRACT, armour_class=0), attribute], 10),
                trigger(4, [effect(aoe2mc.CHANGE_OBJECT_ARMOR, 3, SET, armour_class=0)], 60)]
    assert lines(triggers, 4) == [
        f"{AT} run attribute @s minecraft:armor modifier remove aoe2mc:trig_3_0",
        f"{AT} run attribute @s minecraft:armor modifier remove aoe2mc:trig_3_1",
        f"{AT} run attribute @s minecraft:armor base set 3"]


def test_a_set_to_0_is_a_base_set_and_a_set_with_no_earlier_effect_only_sets():
    assert lines([trigger(4, [effect(aoe2mc.CHANGE_OBJECT_ARMOR, 0, SET)], 60)], 4) == \
        [f"{AT} run attribute @s minecraft:armor base set 0"]
