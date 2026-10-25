"""find_spawn: start view of player 1, else in front of its town center, else the map center (#16)."""
import numpy as np

import aoe2mc


def cols(water_west=False):
    t = np.zeros((20, 20), np.int16)
    if water_west:
        t[:6] = 1
    return aoe2mc.Columns(20, t, np.zeros((20, 20), np.float32), {0: "GRASS_1", 1: "WATER_DEEP"}, 4, 2,
                          np.random.default_rng(1))


TC = dict(kind="B", name="TOWN_CENTER", player=1, x=6.0, y=6.0)


def test_start_view_wins():
    x, y, z = aoe2mc.find_spawn(cols(), [TC], {1: {"view": (15, 3)}})
    assert (x, z) == (60, 12)
    assert y == cols().surface(60, 12) + 2


def test_in_front_of_the_town_center():
    c = cols()
    c.blocked[16:32, 16:32] = True                  # the town center (4 x 4 tiles)
    x, _, z = aoe2mc.find_spawn(c, [dict(TC, player=2), TC], {1: {"view": None}})
    assert (x, z) == (24, 34) and not c.blocked[x, z]


def test_map_center_and_free_land():
    assert aoe2mc.find_spawn(cols(), [], {})[::2] == (40, 40)
    x, _, z = aoe2mc.find_spawn(cols(water_west=True), [], {1: {"view": (1, 10)}})
    assert x >= 24 and z == 40                      # moved out of the water to the nearest land


def test_option_overrides():
    assert aoe2mc.find_spawn(cols(), [TC], {1: {"view": (15, 3)}}, (2, 2))[::2] == (8, 8)
    assert aoe2mc.spawn_spec("12,30") == (12.0, 30.0)
