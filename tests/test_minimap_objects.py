"""Buildings, units and mines on the locked map in the player colors (#840): aoe2mc.map_objects."""
import numpy as np

import aoe2mc

PLAYERS = {0: {"color": "light_gray"}, 1: {"color": "blue"}, 2: {"color": "red"}}


def draw(objects, s=0, c=64):
    return aoe2mc.map_objects(np.full((128, 128), 4, np.uint8), s, c, objects, PLAYERS, T=4)


def test_building_is_the_square_of_its_footprint():
    col = draw([{"kind": "B", "name": "HOUSE", "player": 2, "x": 3, "y": 4, "footprint": [12, 16, 20, 24]}])
    assert (col[16:24, 12:20] == 28 * 4 + 2).all()                    # COLOR_RED, shade 2
    assert (col[15, 12:20] == 4).all() and (col[16:24, 20] == 4).all()


def test_unit_is_one_pixel_on_top_of_a_building():
    col = draw([{"kind": "U", "name": "VILLAGER", "player": 1, "x": 4.5, "y": 5.0},
                {"kind": "B", "name": "HOUSE", "player": 2, "x": 4, "y": 5, "footprint": [16, 20, 24, 28]}])
    assert col[20, 18] == 25 * 4 + 2 and (col == 25 * 4 + 2).sum() == 1    # COLOR_BLUE over the red house
    assert (col == 28 * 4 + 2).sum() == 63


def test_gaia_keeps_the_terrain_except_mines():
    col = draw([{"kind": "U", "name": "SHEEP", "player": 0, "x": 2, "y": 2},
                {"kind": "B", "name": "RUINS", "player": 0, "x": 5, "y": 5, "footprint": [20, 20, 24, 24]},
                {"kind": "O", "name": "GOLD_MINE", "player": 0, "x": 10, "y": 10},
                {"kind": "O", "name": "STONE_MINE", "player": 0, "x": 12, "y": 10}])
    assert col[40, 40] == aoe2mc.MAP_MINES["GOLD_MINE"] * 4 + 2 and col[40, 48] == aoe2mc.MAP_MINES["STONE_MINE"] * 4 + 2
    assert (col != 4).sum() == 2


def test_small_objects_keep_one_pixel_at_scale_4():
    # scale 4: one pixel holds 16 x 16 blocks; the map shows blocks c - 1024 to c + 1023
    col = draw([{"kind": "B", "name": "HOUSE", "player": 1, "x": 1, "y": 1, "footprint": [4, 4, 8, 8]},
                {"kind": "U", "name": "VILLAGER", "player": 2, "x": 100, "y": 100}], s=4, c=1024)
    assert col[0, 0] == 25 * 4 + 2 and col[25, 25] == 28 * 4 + 2 and (col != 4).sum() == 2


def test_garrisoned_unit_does_not_show():
    col = draw([{"kind": "U", "name": "VILLAGER", "player": 1, "x": 2, "y": 2, "garrisoned": True}])
    assert (col == 4).all()


def test_player_colors_have_a_map_color():
    assert all(c in aoe2mc.MAP_DYES for c in aoe2mc.PLAYER_COLORS)
    # MapColor.java: COLOR_BLUE 0x334CB2, COLOR_RED 0x993333, COLOR_YELLOW 0xE5E533
    assert [aoe2mc.MAP_COLORS[aoe2mc.MAP_DYES[c]] for c in ("blue", "red", "yellow")] == [0x334CB2, 0x993333, 0xE5E533]
    assert all(0 < c < len(aoe2mc.MAP_COLORS) for c in aoe2mc.MAP_MINES.values())
