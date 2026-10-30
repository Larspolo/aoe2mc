"""The resources of a DE map find a free tile: a grouping attribute without number_of_groups makes one group (#4699)."""
import pytest

import rmap

# The facts of the start resources of Arabia: the distances and groups of each resource, not the game script.
ARABIA = """<LAND_GENERATION>
base_terrain DIRT
create_player_lands { terrain_type GRASS land_percent 25 base_size 9 border_fuzziness 15 }
<OBJECTS_GENERATION>
create_object TOWN_CENTER { set_place_for_every_player group_placement_radius 18 max_distance_to_players 0 }
create_object VILLAGER { set_place_for_every_player min_distance_to_players 6 max_distance_to_players 6 }
create_object SCOUT { set_place_for_every_player min_distance_to_players 7 max_distance_to_players 9 }
create_object FORAGE { number_of_objects 6 group_placement_radius 3 set_tight_grouping set_gaia_object_only
  set_place_for_every_player min_distance_to_players 10 max_distance_to_players 12 min_distance_group_placement 6 }
create_object GOLD { number_of_objects 7 group_placement_radius 3 set_tight_grouping set_gaia_object_only
  set_place_for_every_player min_distance_to_players 12 max_distance_to_players 16 min_distance_group_placement 7
  max_distance_to_other_zones 7 }
create_object STONE { number_of_objects 5 group_placement_radius 2 set_tight_grouping set_gaia_object_only
  set_place_for_every_player min_distance_to_players 14 max_distance_to_players 18 min_distance_group_placement 7
  max_distance_to_other_zones 7 }
create_object RELIC { number_of_objects 5 min_distance_to_players 25 temp_min_distance_group_placement 20 }
"""


def near(objs, name, st):
    return [o for o in objs if o["name"] == name and max(abs(o["x"] - st["x"]), abs(o["y"] - st["y"])) <= 20]


def joined(objs):
    """True when each object is next to another one (one tight group)."""
    return all(any(p is not o and max(abs(p["x"] - o["x"]), abs(p["y"] - o["y"])) <= 1 for p in objs) for o in objs)


@pytest.mark.parametrize("seed", range(1, 6))
def test_start_resources_of_each_player_find_a_free_tile(seed):
    warnings = []
    m = rmap.generate(ARABIA, seed, players=2, warn=warnings.append)
    assert not [w for w in warnings if "no free tile" in w]
    for st in m["lands"]:
        for name, count in (("FORAGE_BUSH", 6), ("GOLD_MINE", 7), ("STONE_MINE", 5)):
            group = near(m["objects"], name, st)
            assert len(group) == count and joined(group), (name, group)


def test_objects_with_no_grouping_stay_single():
    relics = [o for o in rmap.generate(ARABIA, 1, players=2, warn=lambda m: None)["objects"] if o["name"] == "RELIC"]
    assert len(relics) == 5
    assert all(max(abs(a["x"] - b["x"]), abs(a["y"] - b["y"])) > 20 for a in relics for b in relics if a is not b)
