"""The converter writes the victory setting of a DE scenario (tab "Global Victory") into aoe2mc.json (#2566): the
names of run.VICTORIES, "custom" when only the triggers end the game."""
import contextlib
import io
import json

import pytest
from AoE2ScenarioParser.datasets.trigger_lists import VictoryCondition

import aoe2mc
from tools import scenarios


def victory(tmp_path, condition, **values):
    scn = scenarios.new_scenario(24)
    scn.option_manager.victory_condition = condition
    for k, v in values.items():
        setattr(scn.option_manager, k, v)
    src = scenarios.save(scn, str(tmp_path / "v.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        return json.load(f).get("victory")


def test_a_time_limit_writes_its_years(tmp_path):
    assert victory(tmp_path, VictoryCondition.TIME_LIMIT, victory_years=300) == {"condition": "time-limit", "years": 300}


def test_a_score_condition_writes_its_score(tmp_path):
    assert victory(tmp_path, VictoryCondition.SCORE, victory_score=4000) == {"condition": "score", "score": 4000}


@pytest.mark.parametrize("condition, name", [(VictoryCondition.STANDARD, "standard"),
                                             (VictoryCondition.CONQUEST, "conquest"),
                                             (VictoryCondition.CUSTOM, "custom")])
def test_the_other_conditions_write_only_their_name(tmp_path, condition, name):
    assert victory(tmp_path, condition) == {"condition": name}


def test_the_names_are_victories_of_the_game_program():
    from game import run
    assert {"standard", "conquest", "score", "time-limit"} <= set(run.VICTORIES)
