"""The trigger effect "Count Units into Variable" puts the number of units of a player in an area into the score
#v<N> of aoe_var in the converted world (aoe2mc.count_lines, #2697)."""
import os
import sys
from collections import Counter

import numpy as np
from AoE2ScenarioParser.datasets.effects import EffectId

import aoe2mc
from test_trigger_damage import lines

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import scenarios  # noqa: E402


def effect(variable=3, name=None, player=1, area=(2, 3, 4, 5)):
    return dict(type=aoe2mc.COUNT_UNITS_INTO_VARIABLE, message="", player=player, time=0,
                object=("U", name) if name else None, tile=[-1, -1], area=list(area), variable2=variable)


def test_the_units_of_player_1_in_the_area_go_into_variable_3():
    stats = Counter()
    line, = lines([effect()], stats)
    assert line == ("execute store result score #v3 aoe_var if entity "
                    "@e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=8,y=-64,z=12,dx=11,dy=383,dz=11]")
    assert stats == Counter({"count units into variable": 1})


def test_no_area_counts_the_whole_map():
    line, = lines([effect(area=(-1, -1, -1, -1))])
    assert line == "execute store result score #v3 aoe_var if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount]"


def test_a_unit_type_filters_the_entity_type_and_gaia_is_not_the_players():
    assert lines([effect(name="MILITIA")])[0].startswith(
        "execute store result score #v3 aoe_var if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t74,")
    assert "tag=aoe2mc.p0," in lines([effect(player=0)])[0]   # Gaia: p0 (#2916)


def test_the_load_function_starts_the_variable_at_0():
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=[effect(variable=5)])
    load = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, Counter())[0]
    assert load[:2] == ["scoreboard objectives add aoe_var dummy", "scoreboard players add #v5 aoe_var 0"]


def test_no_variable_writes_no_line():
    stats = Counter()
    assert lines([effect(variable=-1)], stats) == []
    assert stats == Counter({"count units into variable (not supported)": 1})


def test_read_scenario_keeps_the_variable_of_the_effect(tmp_path):
    scn = scenarios.new_scenario(24)
    t = scn.trigger_manager.add_trigger("Count")
    t.new_condition.timer(timer=5)
    t._add_effect(EffectId.COUNT_UNITS_INTO_VARIABLE, source_player=2, variable2=4)
    e, = aoe2mc.read_scenario(scenarios.save(scn, str(tmp_path / "count.aoe2scenario")))[4]["triggers"][0]["effects"]
    assert (e["type"], e["player"], e["variable2"]) == (aoe2mc.COUNT_UNITS_INTO_VARIABLE, 2, 4)
