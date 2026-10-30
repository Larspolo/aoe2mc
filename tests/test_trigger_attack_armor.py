"""The trigger effects "Change Object Attack" and "Change Object Armor" change the attack and the armor of the units of
their player in their area in the converted world (#2755)."""
import contextlib
import io
from collections import Counter

import numpy as np
from test_trigger_unit_values import unit_value

import aoe2mc
from tools import scenarios


def effect(type_, quantity, operation=2, armour_class=4, player=1, area=(2, 3, 4, 5)):
    return dict(type=type_, message="", player=player, time=0, object=None, tile=[-1, -1], area=list(area),
                quantity=quantity, operation=operation, armour_class=armour_class)


def lines(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)[1]
    return [x for x in files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines() if not unit_value(x)]


AT = "execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11]"


def test_change_object_attack_adds_to_the_attack_damage_of_the_units():
    stats = Counter()
    found = lines([effect(aoe2mc.CHANGE_OBJECT_ATTACK, 2)], stats)
    assert found == [f"{AT} run attribute @s minecraft:attack_damage modifier add aoe2mc:trig_7_0 2 add_value"]
    assert stats == Counter({"change object attack": 1})


def test_change_object_armor_subtracts_from_the_armor_of_the_units():
    stats = Counter()
    found = lines([effect(aoe2mc.CHANGE_OBJECT_ARMOR, 1, operation=3, armour_class=0)], stats)
    assert found == [f"{AT} run attribute @s minecraft:armor modifier add aoe2mc:trig_7_0 -1 add_value"]
    assert stats == Counter({"change object armor": 1})


def test_a_multiply_is_not_supported_yet():                            # a set: tests/test_trigger_attack_set.py
    stats = Counter()
    assert lines([effect(aoe2mc.CHANGE_OBJECT_ATTACK, 2, operation=4)], stats) == []
    assert stats == Counter({"change object attack or armor (not supported yet)": 1})


def test_an_attack_class_other_than_3_or_4_is_not_supported_yet():
    stats = Counter()
    assert lines([effect(aoe2mc.CHANGE_OBJECT_ATTACK, 2, armour_class=0)], stats) == []
    assert stats == Counter({"change object attack or armor (not supported yet)": 1})


def test_read_scenario_keeps_the_amount_and_the_class(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Attack")
    t.new_condition.timer(timer=1)
    t.new_effect.change_object_attack(armour_attack_quantity=2, armour_attack_class=4, operation=2, source_player=1,
                                      area_x1=2, area_y1=3, area_x2=4, area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.CHANGE_OBJECT_ATTACK and e["quantity"] == 2 and e["armour_class"] == 4
    assert e["operation"] == 2 and e["area"] == [2, 3, 4, 5]
