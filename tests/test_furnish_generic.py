"""The generic fallback building is furnished inside (#498)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc
import buildings

NAME = "UNKNOWN_BUILDING"                                # select() gives generic() for a name it does not know


def test_name_goes_to_generic():
    assert buildings.select(NAME)[0] is buildings.generic


@pytest.mark.parametrize("arch", ["western", "east_asian", "middle_eastern"])
def test_generic_is_furnished(arch):
    last = blocks(NAME, arch)
    names = Counter(s.split("[")[0] for s in last.values())
    assert names["barrel"] >= 2 and names["chest"] >= 1 and names["lantern"] >= 1, names
    assert not any(n.endswith("_bed") for n in names)
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_cell_inside_the_door_stays_free():
    last = blocks(NAME, "western")
    (x, y, z), = [p for p, s in last.items() if s.endswith("_door") or ("_door[" in s and "half=lower" in s)]
    for dz in (1, 2):
        s = last.get((x, y, z - dz), "air")
        assert s in ("air", "barrier") or s.endswith("_carpet"), (dz, s)


@pytest.mark.parametrize("tile", [1, 2, 3])
def test_small_tile_sizes_work(tile):
    blocks(NAME, "western", tile)
