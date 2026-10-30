"""color_correction, enable_waves and water_definition of a random map script (#4430)."""
import json

import pytest

import aoe2mc
import rmap

LOOK = "<LAND_GENERATION>\nbase_terrain GRASS\ncolor_correction CC_NIGHT\nenable_waves 0\nwater_definition WATERDEF_X\n"


def test_color_correction_gives_the_mood_and_the_water_commands_no_warning():
    d = rmap.generate(LOOK, 1, size=60, warn=lambda m: pytest.fail(m))
    assert d["mood"] == "NIGHT"
    assert aoe2mc.map_description(d, "x")[4]["mood"] == "NIGHT"


def test_an_unknown_color_correction_warns_and_gives_no_mood():
    said = []
    d = rmap.generate("<LAND_GENERATION>\ncolor_correction CC_LAVA\n", 1, size=60, warn=said.append)
    assert "mood" not in d and any("CC_LAVA" in m for m in said)


@pytest.mark.slow
def test_the_converted_world_has_the_mood(tmp_path):
    rms = tmp_path / "look.rms"
    rms.write_text(LOOK)
    aoe2mc.main([str(rms), str(tmp_path / "W")])
    assert json.loads((tmp_path / "W" / "aoe2mc.json").read_text())["mood"] == "NIGHT"
