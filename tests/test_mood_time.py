"""The time of day of a converted world from the map color mood of a DE scenario (#1595, epic #1593): Night and
Darkness at midnight, Evening and Twilight at sunset, the others at noon; --mood off keeps noon."""
import os

import aoe2mc
import pytest
import scenarios
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood
from nbtlib import File


def ticks(world):
    data = File.load(os.path.join(world, "data", "minecraft", "world_clocks.dat"), gzipped=True)
    return int(data["data"]["minecraft:overworld"]["total_ticks"])


@pytest.fixture(scope="module")
def night(tmp_path_factory):
    scn = scenarios.new_scenario(16)
    scn.map_manager.map_color_mood = ColorMood.NIGHT
    return scenarios.save(scn, str(tmp_path_factory.mktemp("mood") / "night.aoe2scenario"))


def test_moods_has_each_color_mood():
    assert set(aoe2mc.MOODS) == {m.name for m in ColorMood}
    assert list(aoe2mc.MOODS) == sorted(aoe2mc.MOODS)
    assert aoe2mc.MOODS["NIGHT"] == aoe2mc.MOODS["DARKNESS"] == 18000 and aoe2mc.MOODS["DEFAULT"] == 6000
    assert aoe2mc.MOODS["EVENING"] == 12500 and aoe2mc.MOODS["TWILIGHT"] == 13000


def test_a_night_scenario_starts_at_midnight_and_mood_off_at_noon(night, tmp_path):
    aoe2mc.convert(night, str(tmp_path / "N"))
    aoe2mc.convert(night, str(tmp_path / "O"), mood="off")
    assert (ticks(tmp_path / "N"), ticks(tmp_path / "O")) == (18000, 6000)


def test_the_tiny_world_stays_at_noon(tiny_world):
    assert ticks(tiny_world[0]) == 6000
