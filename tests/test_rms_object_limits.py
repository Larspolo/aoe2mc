"""The terrain, distance and scale limits of create_object in a random map script (#3857)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DESERT land_percent 30 }
<OBJECTS_GENERATION>
"""


def run(objs, seed=1, size=100, players=2, land=LAND):
    return rmap.generate(land + objs, seed, players=players, size=size, warn=lambda m: pytest.fail(m))


@pytest.mark.parametrize("seed", range(1, 4))
def test_terrain_to_place_on_desert(seed):
    d = run("create_object GOLD { number_of_objects 20 terrain_to_place_on DESERT }", seed)
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert len(gold) == 20
    terrain = np.asarray(d["terrain"])
    assert all(terrain[int(o["x"]), int(o["y"])] == rmap.TERRAINS["DESERT"] for o in gold)


@pytest.mark.parametrize("seed", range(1, 4))
def test_min_distance_group_placement(seed):
    text = ("create_object STONE { number_of_objects 1 }\n"
            "create_object GOLD { number_of_objects 3 number_of_groups 6 set_tight_grouping min_distance_group_placement 5 }")
    objs = [o for o in run(text, seed)["objects"] if o["name"] in ("GOLD_MINE", "STONE_MINE")]
    gold = [o for o in objs if o["name"] == "GOLD_MINE"]
    assert len(gold) == 18
    # each gold tile is 5 tiles from each object of another group: the near ones are its own group of 3
    for o in gold:
        near = [p for p in objs if max(abs(p["x"] - o["x"]), abs(p["y"] - o["y"])) <= 5]
        assert len(near) <= 3 and all(p["name"] == "GOLD_MINE" for p in near)


PLAYERS = "<LAND_GENERATION>\nbase_terrain GRASS\ncreate_player_lands { land_percent 100 }\n<OBJECTS_GENERATION>\n"


def count(text, **kw):
    return sum(o["name"] == "DEER" for o in run(text, **kw)["objects"])


def test_scaling_to_map_size():
    text = "create_object DEER { number_of_objects 4 set_scaling_to_map_size }"
    assert count(text, size=100) == 4 and count(text, size=200) == 16


def test_scaling_to_player_number():
    text = "create_object DEER { number_of_objects 2 number_of_groups 2 set_scaling_to_player_number }"
    assert count(text, players=2, size=144, land=PLAYERS) == 8 and count(text, players=4, size=144, land=PLAYERS) == 16


def test_max_distance_to_other_zones():
    d = run("create_object DEER { number_of_objects 5 set_place_for_every_player max_distance_to_other_zones 4 }",
            land=PLAYERS)
    deer = [o for o in d["objects"] if o["name"] == "DEER"]
    assert len(deer) == 10
    assert np.all([o["player"] for o in deer])
