"""avoid_other_land_zones with no argument in a random map script: AoE2 DE accepts it (Glacis, #5315)."""
import rmap

SCRIPT = """<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT base_size 6 }
<OBJECTS_GENERATION>
create_object GOLD { number_of_objects 4 avoid_other_land_zones }
"""


def test_no_argument():
    d = rmap.generate(SCRIPT, 1, players=2, size=60, warn=lambda m: None)
    assert any(o["name"] == "GOLD_MINE" for o in d["objects"])
