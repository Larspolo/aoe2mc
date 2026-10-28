"""The trigger effect "Replace Object" turns the units of a player in an area into another unit type of the target
player in the converted world (#2703): a summon of the new entity at each old unit, then a kill of the old units."""
import contextlib
import io
from collections import Counter

import numpy as np
from AoE2ScenarioParser.datasets.units import UnitInfo

import aoe2mc
from tools import scenarios


def effect(old="ARCHER", new=("U", "CROSSBOWMAN"), player=1, target=2, area=(2, 3, 4, 5)):
    return dict(type=aoe2mc.REPLACE_OBJECT, message="", player=player, time=0, object=("U", old) if old else None,
                tile=[-1, -1], area=list(area), target=target, object2=new)


def lines(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    players = {1: {"color": "blue"}, 2: {"color": "red"}}
    files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), players, stats)[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_archers_of_player_1_become_crossbowmen_of_player_2():
    stats = Counter()
    mark, summon, kill = lines([effect()], stats)
    archers = aoe2mc.effect_units(effect(), 4)[0]
    assert mark == f"tag {archers} add aoe2mc.replace"
    assert archers.startswith("@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t4,") and "x=8," in archers
    assert summon.startswith("execute at @e[tag=aoe2mc.replace] run summon minecraft:skeleton ~ ~ ~ {")
    assert "aoe2mc.p2" in summon and "aoe2mc.p1" not in summon and "UUID" not in summon
    assert kill == "kill @e[tag=aoe2mc.replace]"                       # only the old units: not the new ones
    assert stats == Counter(replace=1)


def test_a_mounted_unit_loses_its_horse_too():
    out = lines([effect(old="KNIGHT", new=("U", "CAVALIER"), target=1)])
    assert out[-2:] == ["execute as @e[tag=aoe2mc.replace] on vehicle run kill @s", "kill @e[tag=aoe2mc.replace]"]
    assert "Passengers" in out[1]                                      # the new rider sits on a new horse


def test_a_new_type_with_no_entity_is_not_supported_yet():
    stats = Counter()
    assert lines([effect(new=("B", "HOUSE"))], stats) == [] and stats == Counter({"replace (not supported yet)": 1})


def test_read_scenario_keeps_the_new_type_and_the_target_player(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Upgrade")
    t.new_condition.timer(timer=1)
    t.new_effect.replace_object(object_list_unit_id=UnitInfo.ARCHER.ID, object_list_unit_id_2=UnitInfo.CROSSBOWMAN.ID,
                                source_player=1, target_player=2, area_x1=2, area_y1=3, area_x2=4, area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "r.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.REPLACE_OBJECT and e["object"] == ("U", "ARCHER")
    assert e["object2"] == ("U", "CROSSBOWMAN") and e["target"] == 2 and e["area"] == [2, 3, 4, 5]
