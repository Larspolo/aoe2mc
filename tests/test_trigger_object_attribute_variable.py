"""The trigger effect "Modify Object Attribute by Variable" changes one value of the units of its player in its area by
the score of a trigger variable (#2861): hit points by a score operation, armor and attack by a macro modifier."""
import contextlib
import io
from collections import Counter

import numpy as np

import aoe2mc
from test_trigger_unit_values import unit_value
from tools import scenarios

HP, SPEED, ARMOR, ATTACK = 0, 5, 8, 9
SET, ADD, SUBTRACT, DIVIDE = 1, 2, 3, 5
AT = "@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11]"


def effect(attribute, operation, variable=3, armour_class=4):
    return dict(type=aoe2mc.MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE, message="", player=1, time=0, object=None,
                tile=[-1, -1], area=[2, 3, 4, 5], attribute=attribute, operation=operation, variable=variable,
                armour_class=armour_class)


def build(effects, stats=None):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)


def lines(effects, stats=None):
    return [x for x in build(effects, stats)[1].get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()
            if not unit_value(x)]


def test_hit_points_add_the_score_of_the_variable():
    stats = Counter()
    setup, files = build([effect(HP, ADD)], stats)[:2]
    assert f"execute as {AT} unless predicate aoe2mc:rider run function aoe2mc:hp/var_add_3" in lines([effect(HP, ADD)])
    f = files["data/aoe2mc/function/hp/var_add_3.mcfunction"].splitlines()
    assert f[0] == "execute store result score #hp aoe_hp run attribute @s minecraft:max_health base get"
    assert "scoreboard players operation #hp aoe_hp += #v3 aoe_var" in f
    assert f[-1] == "function aoe2mc:hp/apply with storage aoe2mc:hp"
    assert files["data/aoe2mc/function/hp/apply.mcfunction"] == "$attribute @s minecraft:max_health base set $(value)\n"
    assert stats["modify object attribute by variable"] == 1


def test_the_hit_points_stay_in_the_limits_of_the_attribute():
    f = build([effect(HP, DIVIDE)])[1]["data/aoe2mc/function/hp/var_divide_3.mcfunction"].splitlines()
    assert "scoreboard players operation #hp aoe_hp /= #v3 aoe_var" in f
    assert "execute if score #hp aoe_hp matches 1025.. run scoreboard players set #hp aoe_hp 1024" in f
    assert "execute if score #hp aoe_hp matches ..0 run scoreboard players set #hp aoe_hp 1" in f


def test_hp_with_a_score_of_10_gives_10_more_hit_points():
    """The function lines on a stub of the scoreboard: a base of 50 and #v3 = 10 give the macro value 60."""
    f = build([effect(HP, ADD)])[1]["data/aoe2mc/function/hp/var_add_3.mcfunction"].splitlines()
    score = {"#v3": 10}
    for line in f:
        w = line.split()
        if line.startswith("execute store result score #hp"):
            score["#hp"] = 50                                          # the base max_health of the unit
        elif w[:3] == ["scoreboard", "players", "operation"]:
            score["#hp"] = {"+=": score["#hp"] + score[w[6]]}[w[5]]
        elif line.startswith("execute store result storage aoe2mc:hp"):
            value = score["#hp"]
    assert value == 60


def test_armor_and_attack_put_the_score_into_a_modifier():
    s = "aoe2mc:object_attribute_by_variable"
    setup, files = build([effect(ARMOR, SUBTRACT, armour_class=3)])[:2]
    assert lines([effect(ARMOR, SUBTRACT, armour_class=3)]) == [
        f'data modify storage {s} attribute set value "minecraft:armor"',
        f'data modify storage {s} id set value "aoe2mc:trig_7_0"',
        f"execute store result storage {s} value int -1 run scoreboard players get #v3 aoe_var",
        f"execute as {AT} run function aoe2mc:object_attribute_by_variable with storage {s}"]
    assert files["data/aoe2mc/function/object_attribute_by_variable.mcfunction"] == \
        "$attribute @s $(attribute) modifier add $(id) $(value) add_value\n"
    assert f"execute store result storage {s} value int 1 run scoreboard players get #v3 aoe_var" in \
        lines([effect(ATTACK, ADD)])


def test_a_set_of_attack_removes_the_modifier_of_the_variable():
    t = [effect(ATTACK, ADD), dict(effect(ATTACK, SET), type=aoe2mc.MODIFY_OBJECT_ATTRIBUTE, aa=5, variable=None)]
    assert f"execute as {AT} run attribute @s minecraft:attack_damage modifier remove aoe2mc:trig_7_0" in lines(t)


def test_speed_and_a_set_of_armor_give_no_line():
    stats = Counter()
    assert lines([effect(SPEED, SET), effect(ARMOR, SET), effect(ATTACK, ADD, armour_class=11)], stats) == []
    assert stats == Counter({"modify object attribute by variable (not supported)": 3})


def test_read_scenario_keeps_the_attribute_and_the_variable(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Attribute")
    t.new_condition.timer(timer=1)
    t.new_effect.modify_object_attribute_by_variable(object_attributes=HP, operation=ADD, variable=3, source_player=1,
                                                     area_x1=2, area_y1=3, area_x2=4, area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE and e["area"] == [2, 3, 4, 5]
    assert (e["attribute"], e["operation"], e["variable"]) == (HP, ADD, 3)
