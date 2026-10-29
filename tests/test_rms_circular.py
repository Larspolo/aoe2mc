"""min and max_distance_to_players measure a square, set_circular_placement a circle (#4136)."""
import numpy as np
import pytest

import rmap

GOLD = """<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type DIRT land_percent 40 base_size 8 }
<OBJECTS_GENERATION>
create_object GOLD { number_of_objects 40 set_gaia_object_only set_place_for_every_player
  min_distance_to_players 10 max_distance_to_players 12 %s}
"""


def distances(text, seed):
    d = rmap.generate(text, seed, players=2, size=100, warn=lambda m: pytest.fail(m))
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE"]
    assert gold
    dx = np.array([[int(o["x"]) - st["x"] for st in d["lands"]] for o in gold])
    dy = np.array([[int(o["y"]) - st["y"] for st in d["lands"]] for o in gold])
    near = np.abs(dx) + np.abs(dy) == (np.abs(dx) + np.abs(dy)).min(1, keepdims=True)  # the land of each mine
    return np.maximum(abs(dx), abs(dy))[near], np.hypot(dx, dy)[near]


@pytest.mark.parametrize("seed", range(1, 4))
def test_a_square_band_by_default(seed):
    square, circle = distances(GOLD % "", seed)
    assert ((square >= 10) & (square <= 12)).all() and (circle > 12).any()


@pytest.mark.parametrize("seed", range(1, 4))
def test_a_circle_band_with_set_circular_placement(seed):
    _, circle = distances(GOLD % "set_circular_placement ", seed)
    assert ((circle >= 10) & (circle <= 12)).all()
