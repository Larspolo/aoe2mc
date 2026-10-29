"""The fog of the fog moods of a DE scenario (#1626, owner decision #1625): Misty, Murky and Brumous get a fog timeline
in the datapack with --fog or --ambience full, and none without them (no "Experimental Settings" warning)."""
import json
import os

import aoe2mc
import pytest
import scenarios
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood

FOG = os.path.join("datapacks", "aoe2mc", "data", "aoe2mc", "timeline", "fog.json")
TAG = os.path.join("datapacks", "aoe2mc", "data", "minecraft", "tags", "timeline", "in_overworld.json")


@pytest.fixture(scope="module")
def misty(tmp_path_factory):
    scn = scenarios.new_scenario(16)
    scn.map_manager.map_color_mood = ColorMood.MISTY
    return scenarios.save(scn, str(tmp_path_factory.mktemp("mood") / "misty.aoe2scenario"))


def files(world):
    return {os.path.relpath(os.path.join(d, f), world) for d, _, fs in os.walk(os.path.join(world, "datapacks"))
            for f in fs}


def test_the_fog_moods():
    assert set(aoe2mc.FOG) <= {m.name for m in ColorMood}
    assert all(s < e for s, e in aoe2mc.FOG.values())


def test_a_misty_scenario_gets_the_fog_only_with_fog_or_full_ambience(misty, tmp_path):
    for name, kw in (("F", {"fog": True}), ("A", {"ambience": "full"}), ("N", {}), ("O", {"fog": True, "mood": "off"})):
        aoe2mc.convert(misty, str(tmp_path / name), **kw)
    with open(tmp_path / "F" / FOG) as f:
        tracks = json.load(f)["tracks"]
    start, end = aoe2mc.FOG["MISTY"]
    assert tracks["minecraft:visual/fog_start_distance"] == {"keyframes": [{"ticks": 0, "value": float(start)}]}
    assert tracks["minecraft:visual/fog_end_distance"]["keyframes"][0]["value"] == float(end)
    with open(tmp_path / "F" / TAG) as f:
        assert json.load(f) == {"values": ["aoe2mc:fog"]}
    assert {FOG, TAG} <= files(tmp_path / "A")
    assert not {FOG, TAG} & (files(tmp_path / "N") | files(tmp_path / "O"))


def test_a_default_scenario_has_no_fog_also_with_fog(tmp_path):
    scn = scenarios.new_scenario(16)
    path = scenarios.save(scn, str(tmp_path / "default.aoe2scenario"))
    aoe2mc.convert(path, str(tmp_path / "D"))
    aoe2mc.convert(path, str(tmp_path / "E"), fog=True)
    assert files(tmp_path / "D") == files(tmp_path / "E") and not {FOG, TAG} & files(tmp_path / "E")
    for f in files(tmp_path / "D"):
        with open(tmp_path / "D" / f, "rb") as a, open(tmp_path / "E" / f, "rb") as b:
            assert a.read() == b.read(), f


def test_fog_and_no_datapack_is_an_error():
    with pytest.raises(SystemExit):
        aoe2mc.main(["in.aoe2scenario", "out", "--fog", "--ambience", "off"])
