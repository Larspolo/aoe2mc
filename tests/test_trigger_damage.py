"""The trigger effect "Damage Object" damages the units of its player in its area in the converted world (#2571)."""
import contextlib
import io
from collections import Counter

import numpy as np

import aoe2mc
from tools import scenarios


def effect(quantity, name=None, player=1, area=(2, 3, 4, 5)):
    return dict(type=aoe2mc.DAMAGE_OBJECT, message="", player=player, time=0, object=("U", name) if name else None,
                tile=[-1, -1], area=list(area), quantity=quantity)


def lines(effects, stats=None, T=4):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=effects)
    files = aoe2mc.trigger_files([t], T, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, stats)[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_damage_object_damages_each_unit_of_the_player_in_the_area():
    stats = Counter()
    line, = lines([effect(20)], stats)
    assert line == ("execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11] "
                    "run damage @s 20")                                # AoE2 hit points: max_health in the game program
    assert stats == Counter(damage=1)


def test_a_unit_type_filters_the_entity_type():
    line, = lines([effect(5, "MILITIA")])
    assert line.startswith("execute as @e[type=minecraft:zombie,tag=aoe2mc.p1,") and line.endswith(" run damage @s 5")


def test_a_gaia_effect_does_not_damage_the_players():
    line, = lines([effect(5, player=0)])
    assert line.startswith("execute as @e[type=!minecraft:player,tag=!aoe2mc.mount,x=8,")


def test_read_scenario_keeps_the_amount(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Hurt")
    t.new_condition.timer(timer=1)
    t.new_effect.damage_object(quantity=20, source_player=1, area_x1=2, area_y1=3, area_x2=4, area_y2=5)
    src = scenarios.save(scn, str(tmp_path / "d.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.DAMAGE_OBJECT and e["quantity"] == 20 and e["area"] == [2, 3, 4, 5]
