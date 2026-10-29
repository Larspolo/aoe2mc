"""find_closest, find_closest_to_map_center and find_closest_to_map_edge of create_object (#4135)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 40 base_size 8 }
<OBJECTS_GENERATION>
"""
GOLD = LAND + """create_object GOLD { number_of_objects 3 set_gaia_object_only set_place_for_every_player
  min_distance_to_players 10 find_closest }
"""


def gold(text, seed):
    d = rmap.generate(text, seed, players=2, size=100, warn=lambda m: pytest.fail(m))
    return d, [o for o in d["objects"] if o["name"] == "GOLD_MINE"]


@pytest.mark.parametrize("seed", range(1, 4))
def test_find_closest_takes_the_nearest_free_distance(seed):
    d, mines = gold(GOLD, seed)
    assert len(mines) == 6
    for st in d["lands"]:
        own = sorted([(int(o["x"]) - st["x"], int(o["y"]) - st["y"]) for o in mines],
                     key=lambda d: np.hypot(*d))[:3]  # a circle or a square band (#4136): both near 10 tiles
        assert all(np.hypot(*d) >= 10 and max(map(abs, d)) <= 11 for d in own), own


def test_the_same_seed_gives_the_same_objects():
    assert gold(GOLD, 5)[1] == gold(GOLD, 5)[1]


def test_find_closest_to_map_center_and_edge():
    _, [mid] = gold(LAND + "create_object GOLD { find_closest_to_map_center }\n", 2)
    assert np.hypot(int(mid["x"]) - 49.5, int(mid["y"]) - 49.5) <= 1
    _, [edge] = gold(LAND + "create_object GOLD { find_closest_to_map_edge }\n", 2)
    assert min(int(edge["x"]), int(edge["y"]), 99 - int(edge["x"]), 99 - int(edge["y"])) == 0
