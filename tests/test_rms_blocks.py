"""The block and constant errors of the random map survey (#4309): each script generates or gives an RmsError."""
import pytest

import rmap

LAND = "<LAND_GENERATION>\nbase_terrain GRASS\n"


def run(text):
    return rmap.generate(text, 1, players=2, size=60, warn=lambda m: None)


def test_const_with_no_value():
    d = run("#const SHORE\n#include_drs random_map.def\n#const DEEP 22\n" + LAND +
            "create_player_lands { terrain_type DEEP land_percent 20 }")
    assert d["lands"]


def test_const_of_a_constant():
    assert run("#const MY_GRASS GRASS\n" + LAND.replace("GRASS", "MY_GRASS"))["terrain"]


def test_negative_clumping_factor():
    assert run(LAND + "create_player_lands { terrain_type DIRT land_percent 40 clumping_factor -10 }")["lands"]


@pytest.mark.parametrize("text", ["endif\n", "if TINY_MAP\n", "start_random percent_chance 50\n",
                                  "end_random\n"])
def test_unbalanced_blocks(text):
    with pytest.raises(rmap.RmsError):
        run(text + LAND)


def test_if_in_a_comment():
    assert run("/* if TINY_MAP */\n/* endif */\n" + LAND)["terrain"]
