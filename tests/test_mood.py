"""The map color mood of a DE scenario (#1594, epic #1593)."""
import json
import os

import scenarios
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood

import aoe2mc


def mood_of(tmp_path, mood):
    scn = scenarios.new_scenario(16)
    scn.map_manager.map_color_mood = mood
    path = scenarios.save(scn, str(tmp_path / "mood.aoe2scenario"))
    return aoe2mc.read_scenario(path)[4]["mood"]


def test_reads_the_night_mood(tmp_path):
    assert mood_of(tmp_path, ColorMood.NIGHT) == "NIGHT"


def test_unknown_mood_gives_its_upper_case_name(tmp_path):
    assert mood_of(tmp_path, "my_custom_mood") == "MY_CUSTOM_MOOD"


def test_tiny_world_has_the_default_mood(tiny_world):
    world, _ = tiny_world
    with open(os.path.join(world, "aoe2mc.json")) as f:
        assert json.load(f)["mood"] == "DEFAULT"
