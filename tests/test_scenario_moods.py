"""tools/scenarios.py moods: the village scenario with a map color mood, for a check of the moods in the game (#1598,
epic #1593)."""
import contextlib
import io
import os
import subprocess
import sys

import scenarios
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "scenarios.py")


def mood(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(path).map_manager.map_color_mood


def test_the_cli_writes_a_night_village(tmp_path):
    out = str(tmp_path / "night.aoe2scenario")
    subprocess.run([sys.executable, TOOL, "moods", out, "--mood", "NIGHT"], check=True, capture_output=True)
    assert mood(out) == ColorMood.NIGHT


def test_each_mood_name_and_the_village_land(tmp_path):
    out = scenarios.moods(str(tmp_path / "swamp.aoe2scenario"), "swamp")
    assert mood(out) == ColorMood.SWAMP
    assert mood(scenarios.village(str(tmp_path / "village.aoe2scenario"))) in ("", ColorMood.DEFAULT)   # no mood
