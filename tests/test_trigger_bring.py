"""A trigger with the condition "Bring Object to Area" fires in the converted world when its unit is in the area
(#2620): the tick function tests the tag aoe2mc.r<ref> of the unit (#2617) in the box of the area."""
import contextlib
import io
import os
from collections import Counter

from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

CHAT = dict(type=aoe2mc.SEND_CHAT, message="It is there.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
BOX = f"x=4,y={aoe2mc.MIN_Y},z=8,dx=7,dy={aoe2mc.HEIGHT - 1},dz=7"         # tiles 1..2, 2..3 at T = 4


def bring(ref=7, unit=True, area=(2, 3, 1, 2)):
    return dict(type=aoe2mc.BRING_OBJECT_TO_AREA, timer=0, inverted=False, ref=ref, unit=unit, area=list(area))


def tick(conds, stats=None, looping=False):
    t = dict(id=3, name="t", enabled=True, looping=looping, conditions=conds, effects=[CHAT])
    files = aoe2mc.trigger_files([t], stats=stats)[1]
    return files.get("data/aoe2mc/function/tick.mcfunction", "").splitlines(), files


def test_the_tick_function_runs_the_trigger_when_the_unit_is_in_the_area():
    lines, files = tick([bring()])
    assert lines == [f"execute if entity @e[tag=aoe2mc.r7,{BOX}] unless score #3 aoe_trig matches 1 "
                     "run function aoe2mc:trigger/3"]
    assert files["data/aoe2mc/function/trigger/3.mcfunction"].splitlines() == \
        ['tellraw @a {"text": "It is there."}', "scoreboard players set #3 aoe_trig 1"]


def test_a_looping_trigger_fires_again_after_the_unit_left_the_area():
    lines, _ = tick([bring()], looping=True)
    assert lines[-1] == f"execute unless entity @e[tag=aoe2mc.r7,{BOX}] run scoreboard players reset #3 aoe_trig"


def test_a_building_or_no_object_gives_no_trigger():
    stats = Counter()
    for c in (bring(unit=False), bring(ref=-1)):
        assert tick([c], stats)[1] == {}
    assert stats["object condition (not an entity, not supported yet)"] == 2


def test_the_converter_reads_the_object_and_the_area_of_the_condition(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
        knight = next(u for u in scn.unit_manager.units[1] if u.unit_const == UnitInfo.KNIGHT.ID)
        t = scn.trigger_manager.add_trigger("Knight at the hill")
        t.new_condition.bring_object_to_area(unit_object=knight.reference_id, area_x1=1, area_y1=2, area_x2=2, area_y2=3)
        t.new_effect.send_chat(source_player=PlayerId.ONE, message="The knight is there.")
        src = scenarios.save(scn, str(tmp_path / "b.aoe2scenario"))
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function", "tick.mcfunction")) as f:
        assert f"if entity @e[tag=aoe2mc.r{knight.reference_id},{BOX}]" in f.read()
