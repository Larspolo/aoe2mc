"""An own sheep or goat has the wool of its player, as the herdables of AoE2; a Gaia one keeps its color (#1790)."""
import numpy as np
import pytest
from mcvalid import entity_error

import units

PLAYERS = {0: {"color": "light_gray"}, 1: {"color": "blue"}, 2: {"color": "red"}, 3: {"color": "orange"}}


def wool(name, player):
    nbt = units.make_entity(dict(name=name, player=player, rotation=0.0), PLAYERS, (0.5, 0.0, 0.5),
                            np.random.default_rng(1))
    assert entity_error(str(nbt["id"])) is None
    return int(nbt["Color"])


@pytest.mark.parametrize("name", ["SHEEP", "GOAT"])
def test_an_own_herdable_has_the_wool_of_its_player(name):
    assert [wool(name, p) for p in (1, 2, 3)] == [11, 14, 1]       # blue, red, orange dye


def test_a_gaia_herdable_keeps_its_color():
    assert (wool("SHEEP", 0), wool("GOAT", 0)) == (0, 8)


def test_dye_of_a_player():
    assert units.dye(2, PLAYERS) == units.DYES.index("red") == 14
    assert units.dye(0, PLAYERS) == units.dye(9, PLAYERS) == 0
