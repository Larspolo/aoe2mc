"""set_zone_randomly of create_player_lands and the CLIFF cliff_type word (#4934)."""
import numpy as np
import pytest
from test_rms_connections import reach

import rmap

TEXT = """<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS land_percent 10 base_size 3 set_zone_randomly }
<CONNECTION_GENERATION>
create_connect_same_land_zones { replace_terrain WATER SHALLOW }
"""


def test_random_zones_connect_only_the_lands_of_one_zone():
    for seed in range(6):
        d = rmap.generate(TEXT, seed, players=4, size=100, warn=lambda m: pytest.fail(m))
        t = np.array(d["terrain"]) != rmap.TERRAINS["WATER"]
        at = [(st["x"], st["y"]) for st in d["lands"]]
        groups = {frozenset(q for q in at if q in reach(t, p)) for p in at}
        if 1 < len(groups) < len(at):          # some lands share a zone, not all: the zones are random
            return
    pytest.fail("no seed gave shared and separate zones")


def test_cliff_type_cliff_gives_default_cliffs():
    text = "<CLIFF_GENERATION>\ncliff_type CLIFF\nmin_number_of_cliffs 3\nmax_number_of_cliffs 3\n"
    d = rmap.generate(text, 1, players=2, size=100, warn=lambda m: pytest.fail(m))
    names = {o["name"] for o in d["objects"]}
    assert names and all(m.startswith(rmap.CLIFF_TYPES["CLIFF"]) for m in names)
