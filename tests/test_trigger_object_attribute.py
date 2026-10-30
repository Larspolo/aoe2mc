"""The trigger effect "Modify Object Attribute" changes one value of the units of its player in its area, not of the unit
type (#2860): the handlers of "Change Object HP", "Change Object Speed" and "Change Object Armor" and "Attack"."""
import contextlib
import io
from collections import Counter

import numpy as np
from test_trigger_unit_values import unit_value

import aoe2mc
from tools import scenarios

HP, SPEED, ARMOR, ATTACK, SIGHT = 0, 5, 8, 9, 1
SET, ADD, SUBTRACT = 1, 2, 3


def effect(attribute, operation, quantity=0, aa=0, armour_class=4, type_=aoe2mc.MODIFY_OBJECT_ATTRIBUTE):
    return dict(type=type_, message="", player=1, time=0, object=None, tile=[-1, -1], area=[2, 3, 4, 5],
                attribute=attribute, operation=operation, quantity=quantity, aa=aa, armour_class=armour_class)


def build(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    return aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)


def lines(effects, stats=None):
    return [x for x in build(effects, stats)[1].get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()
            if not unit_value(x)]


def test_hit_points_give_the_lines_of_change_object_hp():
    stats = Counter()
    hp = effect(None, ADD, 10, type_=aoe2mc.CHANGE_OBJECT_HP)
    assert lines([effect(HP, ADD, 10)], stats) == lines([hp])
    assert build([effect(HP, ADD, 10)])[1]["data/aoe2mc/function/hp/add_10.mcfunction"]
    assert stats["modify object attribute"] == 1


def test_a_set_of_the_speed_gives_the_lines_of_change_object_speed():
    speed = effect(None, SET, 2, type_=aoe2mc.CHANGE_OBJECT_SPEED)
    assert lines([effect(SPEED, SET, 2)]) == lines([speed]) != []
    assert lines([effect(SPEED, ADD, 2)]) == []                       # Change Object Speed has no operation


def test_armor_and_attack_give_a_modifier_of_their_points():
    at = "execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11]"
    assert lines([effect(ARMOR, SUBTRACT, aa=1, armour_class=3)]) == \
        [f"{at} run attribute @s minecraft:armor modifier add aoe2mc:trig_7_0 -1 add_value"]
    assert lines([effect(ATTACK, ADD, aa=2)]) == \
        [f"{at} run attribute @s minecraft:attack_damage modifier add aoe2mc:trig_7_0 2 add_value"]


def test_an_attribute_with_no_handler_gives_no_line():
    stats = Counter()
    assert lines([effect(SIGHT, ADD, 3)], stats) == []
    assert stats == Counter({"modify object attribute (not supported)": 1})


def test_read_scenario_keeps_the_attribute_and_the_values(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Attribute")
    t.new_condition.timer(timer=1)
    t.new_effect.modify_object_attribute(object_attributes=ARMOR, operation=ADD, armour_attack_quantity=2,
                                         armour_attack_class=4, source_player=1, area_x1=2, area_y1=3, area_x2=4,
                                         area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.MODIFY_OBJECT_ATTRIBUTE and e["area"] == [2, 3, 4, 5]
    assert (e["attribute"], e["operation"], e["aa"], e["armour_class"]) == (ARMOR, ADD, 2, 4)
