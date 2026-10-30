"""create_player_lands with borders: the starts and lands are inside the box (#4719)."""
import rmap

SCRIPT = """<LAND_GENERATION>
base_terrain WATER
create_player_lands { terrain_type GRASS land_percent 40 base_size 3 bottom_border 70 left_border 70 }
<OBJECTS_GENERATION>
create_object VILLAGER { set_place_for_every_player min_distance_to_players 1 max_distance_to_players 3 }
"""


def test_starts_inside_box():
    warns = []
    m = rmap.generate(SCRIPT, 1, players=2, size=100, warn=warns.append)
    n = 100
    x0, y1 = 70 * n // 100, n - 70 * n // 100
    for land in m["lands"]:
        assert x0 <= land["x"] < n and 0 <= land["y"] < y1
        assert m["terrain"][land["x"]][land["y"]] == rmap.TERRAINS["GRASS"]   # the land grew: not the WATER base
    assert not [w for w in warns if "no free tile" in w]
