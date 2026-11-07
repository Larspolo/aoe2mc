"""game/export.py: the export keeps the Global Victory setting of a converted scenario (#6030)."""
import contextlib
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import export  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.trigger_lists import VictoryCondition  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


def convert(src, world):
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        return json.load(f).get("victory")


@pytest.mark.parametrize("cond", list(VictoryCondition))
def test_export_keeps_victory(cond, tmp_path):
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(src)
    om = scn.option_manager
    om.victory_condition, om.victory_score, om.victory_years = cond.value, 1234, 77
    src = scenarios.save(scn, str(tmp_path / "set.aoe2scenario"))
    want = convert(src, str(tmp_path / "W1"))
    assert want["condition"] == cond.name.lower().replace("_", "-")
    back = export.export(str(tmp_path / "W1"), str(tmp_path / "back.aoe2scenario"))
    assert convert(back, str(tmp_path / "W2")) == want


def test_export_keeps_secondary_game_modes(tmp_path):
    from AoE2ScenarioParser.datasets.trigger_lists import SecondaryGameMode
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(src)
    scn.option_manager.secondary_game_modes = sum(m.value for m in list(SecondaryGameMode)[1:3])
    src = scenarios.save(scn, str(tmp_path / "set.aoe2scenario"))
    want = convert(src, str(tmp_path / "W1"))
    assert len(want["modes"]) == 2
    back = export.export(str(tmp_path / "W1"), str(tmp_path / "back.aoe2scenario"))
    assert convert(back, str(tmp_path / "W2")) == want
