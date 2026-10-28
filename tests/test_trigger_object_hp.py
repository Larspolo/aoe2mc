"""The trigger effect "Change Object HP" changes the max_health of the units of its player in its area (#2693)."""
import contextlib
import io
from collections import Counter

import numpy as np
import pytest

import aoe2mc
from tools import scenarios

SET, ADD, SUBTRACT, MULTIPLY, DIVIDE = 1, 2, 3, 4, 5


def effect(operation, quantity, player=1, area=(2, 3, 4, 5)):
    return dict(type=aoe2mc.CHANGE_OBJECT_HP, message="", player=player, time=0, object=None,
                tile=[-1, -1], area=list(area), operation=operation, quantity=quantity)


def build(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    load, files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)
    return load, files


def lines(effects, stats=None):
    return build(effects, stats)[1].get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def function(name, files):
    return files[f"data/aoe2mc/function/{name}.mcfunction"].splitlines()


def test_a_set_is_one_base_set_per_unit():
    line, ride = lines([effect(SET, 2000)])                                  # a rider: its mount (#2976)
    assert line.startswith("execute as @e[tag=aoe2mc.p1,") and line.endswith(
        " run attribute @s minecraft:max_health base set 1024")               # the limit of the attribute
    assert " on vehicle run " in ride


def test_a_set_below_one_is_one():
    line = lines([effect(SET, -5)])[0]
    assert line.endswith(" run attribute @s minecraft:max_health base set 1")


def test_a_set_keeps_a_value_in_range():
    line = lines([effect(SET, 150)])[0]
    assert line.endswith(" run attribute @s minecraft:max_health base set 150")


def test_add_and_subtract_read_the_base_and_set_it_with_the_macro():
    stats = Counter()
    _, files = build([effect(ADD, 20), effect(SUBTRACT, 5)], stats)
    add, _, sub, _ = lines([effect(ADD, 20), effect(SUBTRACT, 5)])
    assert add.endswith(" run function aoe2mc:hp/add_20") and sub.endswith(" run function aoe2mc:hp/subtract_5")
    body = function("hp/add_20", files)
    assert body[0] == "execute store result score #hp aoe_hp run attribute @s minecraft:max_health base get"
    assert "scoreboard players add #hp aoe_hp 20" in body
    assert "function aoe2mc:hp/apply with storage aoe2mc:hp" in body
    assert "scoreboard players remove #hp aoe_hp 5" in function("hp/subtract_5", files)
    assert files["data/aoe2mc/function/hp/apply.mcfunction"] == "$attribute @s minecraft:max_health base set $(value)\n"
    assert stats == Counter({"change object hp": 2})


def test_the_clamp_keeps_the_result_in_one_to_1024():
    _, files = build([effect(ADD, 20)])
    body = function("hp/add_20", files)
    assert "execute if score #hp aoe_hp matches 1025.. run scoreboard players set #hp aoe_hp 1024" in body
    assert "execute if score #hp aoe_hp matches ..0 run scoreboard players set #hp aoe_hp 1" in body


def test_multiply_and_divide_use_a_constant_score():
    _, files = build([effect(MULTIPLY, 3), effect(DIVIDE, 2)])
    assert "scoreboard players operation #hp aoe_hp *= #k aoe_hp" in function("hp/multiply_3", files)
    assert "scoreboard players set #k aoe_hp 2" in function("hp/divide_2", files)
    assert "scoreboard players operation #hp aoe_hp /= #k aoe_hp" in function("hp/divide_2", files)


def test_a_divide_by_zero_is_not_supported():
    stats = Counter()
    assert lines([effect(DIVIDE, 0)], stats) == [] and stats == Counter({"change object hp (not supported yet)": 1})


def test_the_objective_is_added_at_load():
    load, _ = build([effect(ADD, 20)])
    assert "scoreboard objectives add aoe_hp dummy" in load


def test_read_scenario_keeps_the_operation_and_the_amount(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Hp")
    t.new_condition.timer(timer=1)
    t.new_effect.change_object_hp(quantity=20, operation=2, source_player=1,
                                  area_x1=2, area_y1=3, area_x2=4, area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "hp.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.CHANGE_OBJECT_HP and e["operation"] == 2 and e["quantity"] == 20


@pytest.mark.mc
def test_the_hp_functions_change_the_max_health_on_a_server(tmp_path):
    import json
    import os
    import re

    from test_paper import paper_reachable
    from game import run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = str(tmp_path / "W")
    aoe2mc.convert(scenarios.tiny(str(tmp_path / "t.aoe2scenario")), world)
    _, files = build([effect(ADD, 20, area=(0, 0, 23, 23)), effect(DIVIDE, 2, area=(0, 0, 23, 23)),
                      effect(ADD, 2000, area=(0, 0, 23, 23))])
    for path, text in files.items():                                  # the functions of the trigger lines
        dst = os.path.join(world, "datapacks", "aoe2mc", path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w") as f:
            f.write(text if isinstance(text, str) else json.dumps(text))   # the predicate aoe2mc:rider (#2976)
    with run.Game(world) as game:
        game.forceload()
        game.command("scoreboard objectives add aoe_hp dummy")       # the load function of the converted world
        game.command('summon zombie 20 70 20 {Tags:["aoe2mc.hpt"]}')

        def hp():
            return float(re.findall(r"is ([\d.]+)", game.command(
                "attribute @e[tag=aoe2mc.hpt,limit=1] minecraft:max_health base get"))[0])
        assert hp() == 20
        for name in ("add_20", "divide_2", "add_2000"):
            game.command(f"execute as @e[tag=aoe2mc.hpt] run function aoe2mc:hp/{name}")
        assert hp() == 1024                                           # 20 + 20 = 40, 20, then 2020 cut to 1024
