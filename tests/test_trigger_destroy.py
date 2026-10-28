"""A trigger with the condition "Destroy Object" fires in the converted world when its unit is dead (#2618): the tick
function tests the tag aoe2mc.r<ref> of the unit (#2617)."""
import contextlib
import io
import json
import os
from collections import Counter

from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

CHAT = dict(type=aoe2mc.SEND_CHAT, message="It is dead.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
AREA = dict(type=aoe2mc.IN_AREA, timer=0, inverted=False, quantity=1, player=1, area=[1, 2, 2, 3], object=-1,
            group=-1, **{"class": -1})
# the marker of the unit: made where the unit is, then it follows the unit each tick
FOLLOW = ['execute as @e[tag=aoe2mc.r7] at @s unless entity @e[tag=aoe2mc.m7] run summon marker ~ ~ ~ '
          '{Tags:["aoe2mc.m7"]}', "execute as @e[tag=aoe2mc.r7] at @s run tp @e[tag=aoe2mc.m7] ~ ~ ~"]


def destroy(ref=7, unit=True):
    return dict(type=aoe2mc.DESTROY_OBJECT, timer=0, inverted=False, ref=ref, unit=unit)


def trig(conds, looping=False):
    return dict(id=3, name="t", enabled=True, looping=looping, conditions=conds, effects=[CHAT])


def tick(conds, stats=None, looping=False):
    files = aoe2mc.trigger_files([trig(conds, looping)], stats=stats)[1]
    return files.get("data/aoe2mc/function/tick.mcfunction", "").splitlines(), files


def test_the_tick_function_runs_the_trigger_when_the_unit_is_dead():
    lines, files = tick([destroy()])
    assert lines == FOLLOW + ["execute if entity @e[tag=aoe2mc.m7] unless entity @e[tag=aoe2mc.r7] unless score #3 "
                              "aoe_trig matches 1 run function aoe2mc:trigger/3"]
    assert files["data/aoe2mc/function/trigger/3.mcfunction"].splitlines() == \
        ['tellraw @a {"text": "It is dead."}', "scoreboard players set #3 aoe_trig 1"]


def test_with_an_area_condition_both_must_hold():
    sel = aoe2mc.area_selector(AREA, 4)
    lines, _ = tick([destroy(), AREA])
    assert lines == FOLLOW + [f"execute if entity @e[tag=aoe2mc.m7] unless entity @e[tag=aoe2mc.r7] if entity {sel} "
                              "unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3"]


def test_a_looping_trigger_fires_again_only_after_the_unit_is_back():
    lines, _ = tick([destroy()], looping=True)
    assert lines[-1] == "execute if entity @e[tag=aoe2mc.r7] run scoreboard players reset #3 aoe_trig"


def test_no_object_gives_no_trigger():
    stats = Counter()
    assert tick([destroy(ref=-1)], stats)[1] == {}
    assert stats == Counter({"object condition (not an entity, not supported yet)": 1})


def test_the_converter_reads_the_object_of_the_condition(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
        knight = next(u for u in scn.unit_manager.units[1] if u.unit_const == UnitInfo.KNIGHT.ID)
        t = scn.trigger_manager.add_trigger("Dead knight")
        t.new_condition.destroy_object(unit_object=knight.reference_id)
        t.new_effect.send_chat(source_player=PlayerId.ONE, message="The knight is dead.")
        src = scenarios.save(scn, str(tmp_path / "d.aoe2scenario"))
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function", "tick.mcfunction")) as f:
        assert f"unless entity @e[tag=aoe2mc.r{knight.reference_id}]" in f.read()
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        assert any(o.get("ref") == knight.reference_id for o in json.load(f)["objects"])
