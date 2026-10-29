"""create_object VILLAGER with no number_of_objects gives the 3 start villagers of AoE2 DE (#4120)."""
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 40 base_size 8 }
<OBJECTS_GENERATION>
create_object TOWN_CENTER { set_place_for_every_player max_distance_to_players 0 }
"""


@pytest.mark.parametrize("amount, each", [("", 3), ("number_of_objects 5", 5), ("number_of_objects 1", 1)])
def test_start_villagers(amount, each):
    script = LAND + f"create_object VILLAGER {{ {amount} set_place_for_every_player min_distance_to_players 4 max_distance_to_players 8 }}\n"
    d = rmap.generate(script, 1, players=2, size=100, warn=lambda m: pytest.fail(m))
    vills = [o["player"] for o in d["objects"] if o["name"].startswith("VILLAGER")]
    assert sorted(vills) == [1] * each + [2] * each
