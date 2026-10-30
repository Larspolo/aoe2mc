"""The DE placeholder objects of create_object (BLANKOBJECT, PH_*_OFF): a tile and an actor area, no object (#4698)."""
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type FOREST land_percent 30 }
<OBJECTS_GENERATION>
"""
NAME = sorted(rmap.BLANK)[0]


def run(objs, seed=1):
    return rmap.generate(LAND + objs, seed, players=2, size=100, warn=lambda m: pytest.fail(m))


@pytest.mark.parametrize("head", ["", f"#const {NAME} 99999\n"])   # random_map.def gives it an ID that kinds has not
def test_a_placeholder_places_no_object_and_gives_no_warning(head):
    d = rmap.generate(head + LAND + f"create_object {NAME} {{ number_of_objects 3 }}", 1, players=2, size=100,
                      warn=lambda m: pytest.fail(m))
    assert d["objects"] == run("")["objects"]


@pytest.mark.parametrize("seed", range(1, 4))
def test_the_actor_area_of_a_placeholder_takes_later_objects(seed):
    d = run(f"create_object {NAME} {{ number_of_objects 2 actor_area 5 actor_area_radius 4 }}\n"
            "create_object STONE { number_of_objects 6 actor_area_to_place_in 5 }", seed)
    stone = [o for o in d["objects"] if o["name"] == "STONE_MINE"]
    assert len(stone) == 6
    assert {o["name"] for o in d["objects"]} - {"STONE_MINE"} <= {o["name"] for o in run("", seed)["objects"]}
