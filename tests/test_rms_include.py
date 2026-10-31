"""rmap.py: the #include_drs files of a random map script (#4304). The files are own small texts, not game scripts."""
import numpy as np
import pytest

import rmap

SCRIPT = """#include_drs inc/a.inc
<LAND_GENERATION>
base_terrain MY_LAND
if LABEL
  create_land { terrain_type WATER number_of_tiles 40 land_position 50 50 }
endif
"""


def make(tmp_path, script=SCRIPT, folder=True):
    notes = []
    d = rmap.generate(script, 1, size=40, warn=notes.append, folder=str(tmp_path) if folder else None)
    return np.array(d["terrain"]), notes


def test_an_include_file_gives_its_constants_and_labels(tmp_path):
    (tmp_path / "inc").mkdir()
    (tmp_path / "inc" / "a.inc").write_text(f"#const MY_LAND {rmap.TERRAINS['DIRT']}\n#define LABEL\n")
    terrain, notes = make(tmp_path)
    assert notes == []
    assert (terrain == rmap.TERRAINS["DIRT"]).any() and (terrain == rmap.TERRAINS["WATER"]).any()


def test_a_missing_file_gives_no_warning(tmp_path):    # AoE2 DE has no error for it (#5317)
    script = "#include_drs F_Missing.inc\n<LAND_GENERATION> base_terrain DIRT"
    for folder in (True, False):
        assert make(tmp_path, script, folder)[1] == []


def test_an_include_loop_stops_with_an_error(tmp_path):
    (tmp_path / "a.inc").write_text("#include_drs b.inc")
    (tmp_path / "b.inc").write_text("#include_drs a.inc")
    with pytest.raises(rmap.RmsError, match="more than 8 levels"):
        make(tmp_path, "#include_drs a.inc\n<LAND_GENERATION> base_terrain DIRT")
