"""create_object of <OBJECTS_GENERATION> in a random map script: the objects of each player (#3855)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 40 base_size 8 }
"""
OBJECTS = LAND + """<OBJECTS_GENERATION>
create_object TOWN_CENTER { set_place_for_every_player max_distance_to_players 0 }
create_object GOLD { number_of_objects 7 set_gaia_object_only set_place_for_every_player
  min_distance_to_players 12 max_distance_to_players 16 }
create_object VILLAGER { number_of_objects 3 set_place_for_every_player min_distance_to_players 4 max_distance_to_players 6 }
"""


@pytest.mark.parametrize("seed", range(1, 4))
def test_town_centers_at_the_origins_and_gold_around_them(seed):
    d = rmap.generate(OBJECTS, seed, players=2, size=100, warn=lambda m: pytest.fail(m))
    tcs = [o for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    assert sorted((o["player"], o["x"], o["y"]) for o in tcs) == sorted((st["player"], st["x"], st["y"]) for st in d["lands"])
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert len(gold) == 14 and {o["player"] for o in gold} == {0}
    for st in d["lands"]:
        near = [o for o in gold if 12 <= max(abs(int(o["x"]) - st["x"]), abs(int(o["y"]) - st["y"])) <= 16]
        assert len(near) >= 7
    vills = [o for o in d["objects"] if o["name"].startswith("VILLAGER")]
    assert len(vills) == 6 and {o["player"] for o in vills} == {1, 2}


def test_the_same_seed_gives_the_same_objects():
    assert rmap.generate(OBJECTS, 5, size=100)["objects"] == rmap.generate(OBJECTS, 5, size=100)["objects"]


def test_no_object_on_water_or_forest():
    text = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type WATER land_percent 30 base_size 10 land_position 50 50 }
<TERRAIN_GENERATION>
create_terrain FOREST { base_terrain GRASS land_percent 30 number_of_clumps 8 }
<OBJECTS_GENERATION>
create_object STONE { number_of_objects 200 }
"""
    d = rmap.generate(text, 3, size=80, warn=lambda m: pytest.fail(m))
    t = np.array(d["terrain"])
    stone = [o for o in d["objects"] if o["name"] == "STONE_MINE"]
    assert len(stone) == 200
    bad = [rmap.TERRAINS["WATER"], *rmap.FOREST_TREES]
    assert not any(t[int(o["x"]), int(o["y"])] in bad for o in stone)
    assert len({(o["x"], o["y"]) for o in stone}) == 200
