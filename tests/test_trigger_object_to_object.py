"""A trigger with the condition "Bring Object to Object" fires in the converted world when its unit is next to the other
unit (#2771): the tick function tests the tag aoe2mc.r<next> within one tile of the unit with the tag aoe2mc.r<ref>."""
import contextlib
import io
import os
from collections import Counter

from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

CHAT = dict(type=aoe2mc.SEND_CHAT, message="They met.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
NEAR = "at @e[tag=aoe2mc.r7,limit=1] if entity @e[tag=aoe2mc.r9,distance=..4]"       # one tile at T = 4
APART = "at @e[tag=aoe2mc.r7,limit=1] unless entity @e[tag=aoe2mc.r9,distance=..4]"


def meet(ref=7, nxt=9, unit=True, next_unit=True, inverted=False):
    return dict(type=aoe2mc.BRING_OBJECT_TO_OBJECT, timer=0, inverted=inverted, ref=ref, unit=unit, player=1,
                next=nxt, next_unit=next_unit)


def tick(conds, stats=None, looping=False):
    t = dict(id=3, name="t", enabled=True, looping=looping, conditions=conds, effects=[CHAT])
    files = aoe2mc.trigger_files([t], stats=stats)[1]
    return files.get("data/aoe2mc/function/tick.mcfunction", "").splitlines(), files


def test_the_tick_function_runs_the_trigger_when_the_units_are_next_to_each_other():
    lines, files = tick([meet()])
    assert lines == [f"execute {NEAR} unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3"]
    assert files["data/aoe2mc/function/trigger/3.mcfunction"].splitlines() == \
        ['tellraw @a {"text": "They met."}', "scoreboard players set #3 aoe_trig 1"]


def test_a_looping_trigger_fires_again_after_the_units_went_apart():
    lines, _ = tick([meet()], looping=True)
    assert lines[-1] == f"execute {APART} run scoreboard players reset #3 aoe_trig"


def test_an_inverted_condition_fires_while_the_units_are_apart():
    lines, _ = tick([meet(inverted=True)], looping=True)
    assert lines == [f"execute {APART} unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3",
                     f"execute {NEAR} run scoreboard players reset #3 aoe_trig"]


def test_a_building_or_no_object_gives_no_trigger():
    stats = Counter()
    for c in (meet(next_unit=False), meet(nxt=-1), meet(nxt=None), meet(unit=False)):
        assert tick([c], stats)[1] == {}
    assert stats["object condition (not an entity, not supported yet)"] == 4


def test_the_converter_reads_both_objects_of_the_condition(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
        knight = next(u for u in scn.unit_manager.units[1] if u.unit_const == UnitInfo.KNIGHT.ID)
        other = next(u for us in scn.unit_manager.units for u in us
                     if u is not knight and u.unit_const in (UnitInfo.KNIGHT.ID, UnitInfo.VILLAGER_MALE.ID,
                                                             UnitInfo.VILLAGER_FEMALE.ID, UnitInfo.ARCHER.ID))
        t = scn.trigger_manager.add_trigger("Knight meets")
        t.new_condition.bring_object_to_object(unit_object=knight.reference_id, next_object=other.reference_id)
        t.new_effect.send_chat(source_player=PlayerId.ONE, message="The knight is there.")
        src = scenarios.save(scn, str(tmp_path / "b.aoe2scenario"))
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function", "tick.mcfunction")) as f:
        assert f"at @e[tag=aoe2mc.r{knight.reference_id},limit=1] if entity " \
               f"@e[tag=aoe2mc.r{other.reference_id},distance=..4]" in f.read()
