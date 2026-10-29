"""temp_min_distance_group_placement and generate_for_first_land_only of create_object (#4138)."""
import pytest

import rmap

WATER = """#const SHORE_FISH 69
<LAND_GENERATION>
base_terrain WATER
<OBJECTS_GENERATION>
create_object SHORE_FISH { number_of_groups 6 number_of_objects 2 group_placement_radius 1
  temp_min_distance_group_placement 6 }
create_object SHORE_FISH { number_of_objects 40 }
"""


def far(a, b):
    return max(abs(int(a["x"]) - int(b["x"])), abs(int(a["y"]) - int(b["y"])))


@pytest.mark.parametrize("seed", range(1, 4))
def test_the_groups_of_one_command_keep_apart_and_later_commands_come_near(seed):
    d = rmap.generate(WATER, seed, size=40, warn=lambda m: pytest.fail(m))
    fish = d["objects"]
    first, later = fish[:12], fish[12:]
    groups = [first[i:i + 2] for i in range(0, 12, 2)]
    assert len(first) == 12
    for i, g in enumerate(groups):
        for h in groups[i + 1:]:
            assert min(far(a, b) for a in g for b in h) >= 6
    assert any(far(a, b) < 6 for a in later for b in first)


def test_first_land_only():
    text = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 40 base_size 8 }
<OBJECTS_GENERATION>
create_object GOLD { number_of_objects 3 set_place_for_every_player generate_for_first_land_only
  min_distance_to_players 6 max_distance_to_players 10 }
"""
    d = rmap.generate(text, 2, players=4, size=100, warn=lambda m: pytest.fail(m))
    gold = d["objects"]
    assert len(gold) == 3 and len({o["player"] for o in gold}) == 1
    assert gold[0]["player"] == d["lands"][0]["player"]
