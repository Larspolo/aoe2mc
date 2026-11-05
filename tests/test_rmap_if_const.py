"""`if` and `elseif` are true for a defined constant, as in AoE2 DE (#5766): a #const of the script, and the constants of
random_map.def (DLC_PIG: Green Arabia takes the AoE2 DE branch)."""
import numpy as np

import rmap


def expand(text, consts=None, defined=()):
    d = set(defined)
    rmap.expand(rmap.tokens(text), np.random.default_rng(0), d, {} if consts is None else consts, [])
    return d


def words(text, consts=None):
    return rmap.expand(rmap.tokens(text), np.random.default_rng(0), set(), {} if consts is None else consts, [])


def test_if_is_true_for_a_const_of_the_script():
    assert words("#const MY_VALUE 5 if MY_VALUE a else b endif") == ["a"]


def test_elseif_is_true_for_a_const_of_the_script():
    assert words("#const MY_VALUE 5 if NOPE a elseif MY_VALUE b endif") == ["b"]


def test_if_is_false_for_a_name_that_is_neither_a_label_nor_a_const():
    assert words("if NOPE a else b endif") == ["b"]


def test_a_define_behind_a_const_test_defines_the_label():
    d = expand("#const MY_VALUE 5 if MY_VALUE #define DE endif")
    assert "DE" in d


def test_dlc_pig_from_random_map_def_takes_the_de_branch():
    d = expand("if DLC_PIG #define DE endif", consts=dict(rmap.CONSTS))
    assert "DE" in d


def test_dlc_tiger_and_goat_are_constants_too():
    consts = dict(rmap.CONSTS)
    assert words("if DLC_TIGER a endif", consts) == ["a"]
    assert words("if DLC_GOAT a endif", consts) == ["a"]


def test_the_script_of_the_ticket_defines_de():
    script = "if DLC_PIG\n#define DE\nendif\n<LAND_GENERATION>\nbase_terrain GRASS"
    d = expand(script, consts=dict(rmap.CONSTS))
    assert "DE" in d
