"""rmap.py: rnd() and math expressions of a random map script (#4306)."""
import numpy as np
import pytest

import rmap


def consts_of(text, seed=1):
    consts = {}
    rmap.expand(rmap.tokens(text), np.random.default_rng(seed), set(), consts, [])
    return consts


def test_rnd_in_a_const_gives_a_value_of_its_range_and_the_same_for_a_seed():
    values = [consts_of("#const N rnd(4,6)", s)["N"] for s in range(30)]
    assert set(values) == {4, 5, 6}
    assert consts_of("#const N rnd(4,6)", 7) == consts_of("#const N rnd(4,6)", 7)


def test_math_as_an_argument_gives_the_computed_whole_number():
    words = rmap.expand(rmap.tokens("#const N 5 #const F 0.72 a (N * 2 + 1) (32 * 1.1) ( 10 / 4 ) (100 * F)"),
                        np.random.default_rng(1), set(), {}, [])
    consts = {}
    assert [rmap.value(w, consts) for w in words[1:]] == [11, 35, 3, 72]


def test_a_float_const_rounds_where_it_is_used():
    assert rmap.value("F", consts_of("#const F 1.5")) == 2


def test_a_bad_expression_names_its_text():
    for text in ("#const N (3 +)", "#const N (2 * X)", "#const N (1 / 0)"):
        with pytest.raises(rmap.RmsError, match=r"bad math|unknown constant"):
            consts_of(text)


def test_a_script_with_math_generates():
    d = rmap.generate("#const W rnd(30,50)\n<LAND_GENERATION> base_terrain DIRT\n"
                      "create_land { terrain_type WATER number_of_tiles (W * 2) land_position 50 50 }", 1, size=40)
    assert (np.array(d["terrain"]) == rmap.TERRAINS["WATER"]).sum() > 0
