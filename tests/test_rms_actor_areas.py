"""The actor_area_to_place_in and avoid_all_actor_areas attributes of create_object in a random map script (#4134)."""
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type FOREST land_percent 30 }
<OBJECTS_GENERATION>
"""


def run(objs, seed=1, size=100):
    return rmap.generate(LAND + objs, seed, players=2, size=size, warn=lambda m: pytest.fail(m))


def near(a, b, r):
    return max(abs(a["x"] - b["x"]), abs(a["y"] - b["y"])) <= r


@pytest.mark.parametrize("seed", range(1, 4))
def test_actor_area_to_place_in(seed):
    d = run("create_object RELIC { number_of_objects 2 actor_area 5 actor_area_radius 4 }\n"
            "create_object STONE { number_of_objects 6 actor_area_to_place_in 5 }", seed)
    relic = [o for o in d["objects"] if o["name"] == "RELIC"]
    stone = [o for o in d["objects"] if o["name"] == "STONE_MINE"]
    assert len(relic) == 2 and len(stone) == 6
    assert all(any(near(s, r, 4) for r in relic) for s in stone)


@pytest.mark.parametrize("seed", range(1, 4))
def test_avoid_all_actor_areas(seed):
    d = run("create_object RELIC { number_of_objects 2 actor_area 5 actor_area_radius 4 }\n"
            "create_object STONE { number_of_objects 6 avoid_all_actor_areas }", seed)
    relic = [o for o in d["objects"] if o["name"] == "RELIC"]
    stone = [o for o in d["objects"] if o["name"] == "STONE_MINE"]
    assert len(relic) == 2 and len(stone) == 6
    assert not any(near(s, r, 4) for s in stone for r in relic)


@pytest.mark.parametrize("seed", range(1, 3))
def test_same_seed_same_objects(seed):
    objs = ("create_object RELIC { number_of_objects 2 actor_area 5 actor_area_radius 4 }\n"
            "create_object STONE { number_of_objects 6 actor_area_to_place_in 5 }")
    assert run(objs, seed)["objects"] == run(objs, seed)["objects"]
