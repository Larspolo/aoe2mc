"""A DE placeholder on an object (the town center) gives its actor area to the resources, and create_object
finds the land of a land_id of create_land (#4935)."""
import pytest

import rmap

NAME = sorted(rmap.BLANK)[0]
LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 60 base_size 10 }
create_land { terrain_type DESERT land_percent 5 land_id 420 }
<OBJECTS_GENERATION>
create_object TOWN_CENTER { set_place_for_every_player max_distance_to_players 0 }
"""


def run(objs, seed):
    warnings = []
    d = rmap.generate(LAND + objs, seed, players=2, size=100, warn=warnings.append)
    return d, warnings


@pytest.mark.parametrize("seed", range(1, 4))
def test_gold_in_the_actor_area_of_a_placeholder_at_the_town_center(seed):
    d, warnings = run(f"create_object {NAME} {{ set_place_for_every_player max_distance_to_players 0 actor_area 9 "
                      "actor_area_radius 20 }\ncreate_object GOLD { number_of_objects 7 set_tight_grouping "
                      "set_gaia_object_only set_place_for_every_player min_distance_to_players 12 "
                      "max_distance_to_players 16 actor_area_to_place_in 9 }", seed)
    assert not warnings
    assert sum(o["name"].startswith("GOLD") for o in d["objects"]) == 14


@pytest.mark.parametrize("seed", range(1, 4))
def test_create_object_on_the_land_of_a_land_id(seed):
    d, warnings = run("create_object GOLD { number_of_objects 3 place_on_specific_land_id 420 }", seed)
    assert not warnings
    gold = [o for o in d["objects"] if o["name"].startswith("GOLD")]
    assert len(gold) == 3
