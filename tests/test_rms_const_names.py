"""A #const that names a color mood or a cliff type in a DE script (#5248)."""
import rmap
from aoe2mc import MOODS

MOOD = next(iter(MOODS))
CLIFF = next(iter(rmap.CLIFF_TYPES))
BASE = "<LAND_GENERATION>\nbase_terrain GRASS\n"


def warns_of(text):
    warns = []
    rmap.generate(text, 1, size=40, warn=warns.append)
    return warns


def test_a_const_names_a_color_mood():
    warns = []
    out = rmap.generate(f"#const COLOUR_MOOD CC_{MOOD}\n<PLAYER_SETUP>\ncolor_correction COLOUR_MOOD\n{BASE}",
                        1, size=40, warn=warns.append)
    assert out["mood"] == MOOD and warns == []


def test_a_const_names_a_cliff_type():
    assert warns_of(f"#const KIND {CLIFF}\n<CLIFF_GENERATION>\ncliff_type KIND\n{BASE}") == []


def test_a_const_with_an_unknown_value_word_leaves_no_command():
    assert warns_of(f"#const X UNKNOWN_WORD_XYZ\n{BASE}") == []
