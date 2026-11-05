"""max_distance_to_other_zones keeps an object away from the lands of other zones, not from the other lands of its own
zone (#5737). The zones of the RMS guide: create_player_lands gives each player the zone PlayerNumber - 10, and all
create_land lands share the zone -10 (unless the script gives a zone)."""
import pytest

import rmap

# The start mines of Arabia (tests/test_rmap_free_tile.py) on small player lands in a large grass land.
MINES = """<OBJECTS_GENERATION>
create_object TOWN_CENTER { set_place_for_every_player group_placement_radius 18 max_distance_to_players 0 }
create_object GOLD { number_of_objects 7 group_placement_radius 3 set_tight_grouping set_gaia_object_only
  set_place_for_every_player min_distance_to_players 12 max_distance_to_players 16 min_distance_group_placement 7
  max_distance_to_other_zones 7 }
create_object STONE { number_of_objects 5 group_placement_radius 2 set_tight_grouping set_gaia_object_only
  set_place_for_every_player min_distance_to_players 14 max_distance_to_players 18 min_distance_group_placement 7
  max_distance_to_other_zones 7 }
"""


def lands(player_zone, grass_zone):
    return ("<LAND_GENERATION>\nbase_terrain DIRT\n"
            f"create_player_lands {{ terrain_type DIRT land_percent 5 base_size 12 {player_zone} }}\n"
            f"create_land {{ terrain_type GRASS land_percent 90 base_size 5 {grass_zone} }}\n")


def mines(text, seed):
    warnings = []
    m = rmap.generate(text, seed, players=2, size=120, warn=warnings.append)
    return m, [o for o in m["objects"] if o["name"] in ("GOLD_MINE", "STONE_MINE")], warnings


@pytest.mark.parametrize("seed", range(1, 4))
@pytest.mark.parametrize("zones", [("zone 1", "zone 1"), ("zone -10", "")])
def test_lands_of_one_zone_are_no_other_zone(seed, zones):
    m, found, warnings = mines(lands(*zones) + MINES, seed)
    assert not [w for w in warnings if "no free tile" in w]
    for st in m["lands"]:
        near = [o for o in found if max(abs(o["x"] - st["x"]), abs(o["y"] - st["y"])) <= 20]
        assert sorted(o["name"] for o in near) == ["GOLD_MINE"] * 7 + ["STONE_MINE"] * 5

