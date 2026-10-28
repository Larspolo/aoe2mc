"""The trigger effect "Heal Object" heals the units of its player in its area in the converted world (#2692)."""
import contextlib
import io
from collections import Counter

import numpy as np

import aoe2mc
from tools import scenarios


def effect(quantity, name=None, player=1, area=(2, 3, 4, 5), kind="U"):
    return dict(type=aoe2mc.HEAL_OBJECT, message="", player=player, time=0, object=(kind, name) if name else None,
                tile=[-1, -1], area=list(area), quantity=quantity)


def lines(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    load, files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)
    return load, files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_heal_object_raises_the_health_of_each_unit_up_to_its_maximum():
    stats = Counter()
    load, found = lines([effect(20)], stats)
    at = "execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11] unless predicate aoe2mc:rider"
    assert found[:5] == [f"{at} store result score @s aoe_hp run data get entity @s Health",
                     f"{at} store result score @s aoe_max run attribute @s minecraft:max_health get",
                     f"{at} run scoreboard players add @s aoe_hp 20",
                     f"{at} run scoreboard players operation @s aoe_hp < @s aoe_max",
                     f"{at} store result entity @s Health float 1 run scoreboard players get @s aoe_hp"]
    assert stats == Counter(heal=1)
    assert any("scoreboard objectives add aoe_hp dummy" in line for line in load)


def test_a_unit_type_filters_the_entity_type():
    _, found = lines([effect(5, "MILITIA")])
    assert found[2].startswith("execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t74,")
    assert found[2].endswith(" run scoreboard players add @s aoe_hp 5")


def test_a_building_is_not_supported_yet():
    stats = Counter()
    _, found = lines([effect(20, "CASTLE", kind="B")], stats)
    assert found == [] and stats == Counter({"heal (building or no amount, not supported yet)": 1})


def test_read_scenario_keeps_the_amount(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Heal")
    t.new_condition.timer(timer=1)
    t.new_effect.heal_object(quantity=20, source_player=1, area_x1=2, area_y1=3, area_x2=4, area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "h.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.HEAL_OBJECT and e["quantity"] == 20 and e["area"] == [2, 3, 4, 5]
