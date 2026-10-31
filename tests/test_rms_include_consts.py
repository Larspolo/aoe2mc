"""An #include_drs file that is read and defines a name only behind an if: no false warning (#5361)."""
import rmap

INC = """if REGICIDE
#const CLIFF_TYPE 264
#const COLOUR_MOOD 1
endif
"""
SCRIPT = """#include_drs biome.inc
<LAND_GENERATION>
base_terrain GRASS
<CLIFF_GENERATION>
cliff_type CLIFF_TYPE
<LIGHTING>
color_correction COLOUR_MOOD
"""


def test_names_of_a_read_include_behind_an_if_give_no_warning(tmp_path):
    (tmp_path / "biome.inc").write_text(INC)
    out = []
    rmap.generate(SCRIPT, 1, size=40, warn=out.append, folder=str(tmp_path))
    assert [n for n in out if not n.startswith("<")] == []
