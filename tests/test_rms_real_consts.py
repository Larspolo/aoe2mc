"""A #const with a number that stands for a cliff type or a color mood, as in the AoE2 DE includes (#5859):
random_map.def gives the number its name (rmap.IDS), so no warning and the mood is set."""
import rmap

SCRIPT = """#const CLIFF_TYPE {cliff}
#const COLOUR_MOOD {mood}
<LAND_GENERATION>
base_terrain GRASS
<TERRAIN_GENERATION>
color_correction COLOUR_MOOD
<CLIFF_GENERATION>
cliff_type CLIFF_TYPE
min_number_of_cliffs 3
max_number_of_cliffs 5
"""


def run(cliff, mood):
    warns = []
    out = rmap.generate(SCRIPT.format(cliff=cliff, mood=mood), 1, size=40, warn=warns.append)
    return out, warns


def test_a_number_const_names_a_color_mood_and_a_cliff_type_with_no_warning():
    out, warns = run(3, 2)                # CT_MARBLE, CC_WINTER
    assert warns == [] and out["mood"] == "WINTER"


def test_each_cliff_number_of_random_map_def_is_known():
    names = [rmap.IDS[("CT_", n)] for n in range(6)]
    assert all(name in rmap.CLIFF_TYPES for name in names)


def test_an_unknown_cliff_number_still_gives_the_warning():
    _, warns = run(99, 2)
    assert any("has no cliff object" in w for w in warns)
