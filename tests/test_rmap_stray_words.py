"""rmap.py: a note in parentheses after a #define label (Highland) and an undefined base_terrain constant (Aftermath
SPAWN_BLEND) do not stop the script (#4950). The scripts here are own small texts, not scripts of the game."""
import rmap

NOTE = """#define START_STONE (reduced by two)
<LAND_GENERATION>
base_terrain DIRT
"""

BLEND = """<LAND_GENERATION>
base_terrain GRASS
<TERRAIN_GENERATION>
#const MY_BLEND 6
create_terrain MY_BLEND { base_terrain NO_SUCH_WORD number_of_tiles 50 }
"""


def test_define_note_is_skipped():
    notes = []
    land = rmap.generate(NOTE, 1, 2, size=60, warn=notes.append)
    assert land and not [n for n in notes if "reduced" in n]


def test_undefined_base_terrain_reads_as_zero():
    notes = []
    rmap.generate(BLEND, 1, 2, size=60, warn=notes.append)
    assert any("NO_SUCH_WORD" in n and "read as 0" in n for n in notes)
    zero = BLEND.replace("NO_SUCH_WORD", "0")
    assert rmap.generate(BLEND, 1, 2, size=60, warn=[].append) == rmap.generate(zero, 1, 2, size=60, warn=[].append)
