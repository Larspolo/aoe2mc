"""The min_distance_to_map_edge of create_object in a random map script (#4427)."""
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DESERT land_percent 30 }
<OBJECTS_GENERATION>
"""


def run(objs, seed=1, size=100):
    return rmap.generate(LAND + objs, seed, players=2, size=size, warn=lambda m: pytest.fail(m))


@pytest.mark.parametrize("seed", range(1, 4))
def test_min_distance_to_map_edge(seed):
    d = run("create_object GOLD { number_of_objects 30 min_distance_to_map_edge 10 }", seed)
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert len(gold) == 30
    # the tiles are the integer part of the centre (x + 0.5): 10 to 89 keep 10 tiles from the edge at 0 and 99
    assert all(10 <= int(o["x"]) <= 89 and 10 <= int(o["y"]) <= 89 for o in gold)


def test_min_distance_to_map_edge_same_seed():
    text = "create_object GOLD { number_of_objects 30 min_distance_to_map_edge 10 }"
    assert run(text, seed=5)["objects"] == run(text, seed=5)["objects"]
