"""--random-map nomad: one large land with a sea ring at all four map edges, as the AoE2 Nomad map (#2336, AoE2 wiki
"Nomad (map)"); rmap.generate reads the land borders of the RMS language (left_border ...)."""
import numpy as np
import pytest

import rmap

T = rmap.TERRAINS
WATER = [T["WATER"], T["SHALLOW"], T["DEEP_WATER"], T["MED_WATER"]]
SEA = ("FISH", "SHORE_FISH", "DOLPHIN", "MARLIN")                     # the objects of the water


@pytest.mark.parametrize("players", [2, 4, 8])
@pytest.mark.parametrize("seed", [1, 2])
def test_the_map_edges_are_water_and_the_middle_is_land(seed, players):
    t = np.array(rmap.random_map("nomad", seed, players)["terrain"])
    n, k = t.shape[0], 5
    water = np.isin(t, WATER)
    assert water[:k].all() and water[-k:].all() and water[:, :k].all() and water[:, -k:].all()
    assert not water[n // 3:2 * n // 3, n // 3:2 * n // 3].any()


@pytest.mark.parametrize("players", [2, 4, 8])
@pytest.mark.parametrize("seed", [1, 2])
def test_all_villagers_mines_bushes_and_animals_are_on_land(seed, players):
    d = rmap.random_map("nomad", seed, players)
    t = np.array(d["terrain"])
    land = [o for o in d["objects"] if not any(f in o["name"] for f in SEA)]
    assert {"VILLAGER_MALE", "GOLD_MINE", "STONE_MINE", "FORAGE_BUSH"} <= {o["name"] for o in land}
    assert [o["name"] for o in land if t[int(o["x"]), int(o["y"])] in WATER] == []


def test_a_land_stays_in_its_borders():
    text = """<LAND_GENERATION>
base_terrain WATER
create_land { terrain_type GRASS land_position 50 50 land_percent 100 left_border 10 right_border 20 top_border 30
  bottom_border 0 border_fuzziness 100 }
"""
    t = np.array(rmap.generate(text, 1, size=100, warn=pytest.fail)["terrain"])
    rows, cols = np.nonzero(t == T["GRASS"])
    assert (rows.min(), rows.max(), cols.min(), cols.max()) == (10, 79, 30, 99)
