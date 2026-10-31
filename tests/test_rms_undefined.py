"""A command or attribute with an undefined constant is skipped with one warning, as AoE2 DE ignores it (#5172)."""
import numpy as np

import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain DIRT
base_terrain UNDEFINED_TERRAIN
create_land { terrain_type GRASS land_percent 20 base_size UNDEFINED_SIZE }
<OBJECTS_GENERATION>
create_object UNDEFINED_OBJECT { number_of_objects 5 }
create_object UNDEFINED_OBJECT { number_of_objects 3 }
create_object GOLD { number_of_objects 4 }
"""


def make(seed):
    notes = []
    return rmap.generate(SCRIPT, seed, 2, warn=notes.append), notes


def test_an_undefined_constant_skips_its_command_with_one_warning():
    (a, notes), (b, _) = make(3), make(3)
    undefined = sorted(m for m in notes if "is not defined" in m)
    assert [m.split()[1] for m in undefined] == ["UNDEFINED_OBJECT", "UNDEFINED_SIZE", "UNDEFINED_TERRAIN"]
    assert (np.array(a["terrain"]) == np.array(b["terrain"])).all() and a["objects"] == b["objects"]
    terrain = np.array(a["terrain"])
    assert (terrain == rmap.TERRAINS["DIRT"]).any() and (terrain == rmap.TERRAINS["GRASS"]).any()
    assert {o["name"] for o in a["objects"]} == {"GOLD_MINE"}
