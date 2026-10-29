"""The forest zones, actor areas and second objects of create_object in a random map script (#3858)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type FOREST land_percent 30 }
<OBJECTS_GENERATION>
"""


def run(objs, seed=1, size=100):
    return rmap.generate(LAND + objs, seed, players=2, size=size, warn=lambda m: pytest.fail(m))


def forest(d):
    return np.isin(np.asarray(d["terrain"]), list(rmap.FOREST_TREES))


def far(d, o, mask):
    """The square distance (tiles) from object o to the nearest True tile of mask."""
    t = np.argwhere(mask)
    return int(np.max(np.abs(t - [int(o["x"]), int(o["y"])]), axis=1).min())


@pytest.mark.parametrize("seed", range(1, 4))
def test_avoid_forest_zone(seed):
    d = run("create_object GOLD { number_of_objects 20 avoid_forest_zone 4 }", seed)
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert len(gold) == 20 and all(far(d, o, forest(d)) > 4 for o in gold)


@pytest.mark.parametrize("seed", range(1, 4))
def test_place_on_forest_zone(seed):
    d = run("create_object STONE { number_of_objects 10 place_on_forest_zone }", seed)
    stone = [o for o in d["objects"] if o["name"] == "STONE_MINE"]
    assert len(stone) == 10 and all(far(d, o, forest(d)) == 1 for o in stone)


@pytest.mark.parametrize("seed", range(1, 4))
def test_actor_area_and_avoid_actor_area(seed):
    d = run("create_object GOLD { number_of_objects 5 actor_area 7 actor_area_radius 6 }\n"
            "create_object STONE { number_of_objects 30 avoid_actor_area 7 }", seed)
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    stone = [o for o in d["objects"] if o["name"] == "STONE_MINE"]
    assert len(gold) == 5 and len(stone) == 30
    assert all(max(abs(s["x"] - g["x"]), abs(s["y"] - g["y"])) > 6 for s in stone for g in gold)


def test_second_object():
    d = run("create_object GOLD { number_of_objects 4 second_object STONE }")
    gold = sorted((o["x"], o["y"]) for o in d["objects"] if o["name"] == "GOLD_MINE")
    stone = sorted((o["x"], o["y"]) for o in d["objects"] if o["name"] == "STONE_MINE")
    assert len(gold) == 4 and gold == stone
