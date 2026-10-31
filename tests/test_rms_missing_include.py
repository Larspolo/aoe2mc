"""A missing #include_drs file and the undefined constants of it in a random map script (#5317)."""
import rmap

SCRIPT = """#include_drs includes/defend_wonder.inc
<LAND_GENERATION>
base_terrain GRASS
<CLIFF_GENERATION>
cliff_type CLIFF_TYPE
<LIGHTING>
color_correction COLOUR_MOOD
"""


def notes(script):
    out = []
    rmap.generate(script, 1, size=40, warn=out.append)
    return [n for n in out if not n.startswith("<")]


def test_missing_include_and_its_constants_give_no_warning():
    assert notes(SCRIPT) == []


def test_with_no_missing_include_an_unknown_name_still_gives_the_warning():
    got = notes(SCRIPT.split("\n", 1)[1])
    assert any("CLIFF_TYPE" in n for n in got) and any("COLOUR_MOOD" in n for n in got)
