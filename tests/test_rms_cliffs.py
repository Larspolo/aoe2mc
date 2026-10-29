"""<CLIFF_GENERATION> of a random map script: lines of cliff objects on the land (#3850)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 20 base_size 8 }
create_land { terrain_type WATER number_of_tiles 600 base_size 6 land_position 50 50 }
"""
CLIFFS = LAND + """<CLIFF_GENERATION>
min_number_of_cliffs 3
max_number_of_cliffs 3
min_length_of_cliff 4
max_length_of_cliff 6
"""


@pytest.mark.parametrize("seed", range(1, 6))
def test_three_cliff_lines_on_land(seed):
    d = rmap.generate(CLIFFS, seed, size=120, warn=lambda m: pytest.fail(m))
    t = np.array(d["terrain"])
    cliffs = [o for o in d["objects"] if o["name"].startswith("CLIFF_DEFAULT_")]
    lines = {}
    for o in cliffs:
        lines.setdefault(o["line"], []).append(o)
    assert len(lines) == 3 and all(4 <= len(v) <= 6 for v in lines.values())
    for o in cliffs:
        x, y = int(o["x"]), int(o["y"])
        assert o["player"] == 0 and t[x, y] not in (rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"])
        for st in d["lands"]:
            assert max(abs(x - st["x"]), abs(y - st["y"])) > st["base_size"]
    for v in lines.values():                    # the pieces of a line are about 3 tiles apart
        p = np.array([(o["x"], o["y"]) for o in v])
        assert (np.abs(np.diff(p, axis=0)).max(1) == rmap.CLIFF_STEP).all()


def test_the_same_seed_gives_the_same_cliffs():
    assert rmap.generate(CLIFFS, 7, size=120)["objects"] == rmap.generate(CLIFFS, 7, size=120)["objects"]


def test_no_cliff_section_gives_no_cliff():
    assert not [o for o in rmap.generate(LAND, 3, size=120)["objects"] if o["name"].startswith("CLIFF")]


def test_the_converter_knows_the_cliff_names():
    import aoe2mc
    names = {name for _, name in aoe2mc.object_kinds().values()}
    assert all(f"CLIFF_DEFAULT_{k}" in names for k in range(1, 10))
