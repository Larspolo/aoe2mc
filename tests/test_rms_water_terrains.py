"""Each water terrain of AoE2 DE is water for a random map script (#4720)."""
import numpy as np
import pytest

import rmap


def fail(m):
    pytest.fail(m)


def test_fish_on_med_water():
    d = rmap.generate("<LAND_GENERATION>\nbase_terrain MED_WATER\n<OBJECTS_GENERATION>\n"
                      "create_object DORADO { number_of_objects 5 }\n", 1, size=60, warn=fail)
    fish = [o for o in d["objects"] if o["name"] == "FISH_DORADO"]
    terrain = np.array(d["terrain"])
    assert len(fish) == 5
    assert all(terrain[int(o["x"]), int(o["y"])] == rmap.TERRAINS["MED_WATER"] for o in fish)


def test_land_not_on_med_water_and_level_0():
    text = ("<LAND_GENERATION>\nbase_terrain GRASS\n<TERRAIN_GENERATION>\n"
            "create_terrain MED_WATER { base_terrain GRASS land_percent 50 number_of_clumps 1 }\n"
            "<ELEVATION_GENERATION>\ncreate_elevation 4 { base_terrain GRASS number_of_tiles 3000 }\n"
            "<OBJECTS_GENERATION>\ncreate_object GOLD { number_of_objects 200 }\n")
    d = rmap.generate(text, 2, size=60, warn=lambda m: None)
    terrain, elev = np.array(d["terrain"]), np.array(d["elevation"])
    med = terrain == rmap.TERRAINS["MED_WATER"]
    assert med.any() and (elev[med] == 0).all()
    gold = [o for o in d["objects"] if o["name"].startswith("GOLD")]
    assert gold and not any(med[int(o["x"]), int(o["y"])] for o in gold)
