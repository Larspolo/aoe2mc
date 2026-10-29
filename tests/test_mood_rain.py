"""The rain of a converted world from the map color mood of a DE scenario (#1596, epic #1593): Rainforest, Swamp and
Murky have rain (snow in the cold biomes), the other moods and --mood off are clear."""
import os

import aoe2mc
import pytest
import scenarios
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood
from nbtlib import File


def raining(world):
    return int(File.load(os.path.join(world, "data", "minecraft", "weather.dat"), gzipped=True)["data"]["raining"])


@pytest.fixture(scope="module")
def swamp(tmp_path_factory):
    scn = scenarios.new_scenario(16)
    scn.map_manager.map_color_mood = ColorMood.SWAMP
    return scenarios.save(scn, str(tmp_path_factory.mktemp("mood") / "swamp.aoe2scenario"))


def test_only_the_wet_moods_have_rain():
    assert aoe2mc.RAIN <= set(aoe2mc.MOODS)
    assert {m.name for m in ColorMood} >= aoe2mc.RAIN


def test_a_swamp_scenario_rains_and_mood_off_is_clear(swamp, tmp_path):
    aoe2mc.convert(swamp, str(tmp_path / "S"))
    aoe2mc.convert(swamp, str(tmp_path / "O"), mood="off")
    assert (raining(tmp_path / "S"), raining(tmp_path / "O")) == (int("SWAMP" in aoe2mc.RAIN), 0)


def test_the_default_mood_has_its_rain(tiny_world):
    assert raining(tiny_world[0]) == int("DEFAULT" in aoe2mc.RAIN)
