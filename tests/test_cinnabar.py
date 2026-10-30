"""The pagoda and the rekha deul have red-painted stone of cinnabar (#542)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc


@pytest.mark.parametrize("name,arch,needs", [("WONDER", "east_asian", ("polished_cinnabar",)),
                                             ("PAGODA_A", "western", ("polished_cinnabar",)),
                                             ("REKHA_DEUL_TEMPLE", "western", ("cinnabar_bricks", "chiseled_cinnabar"))])
def test_red_stone_is_cinnabar(name, arch, needs):
    names = Counter(s.split("[")[0] for s in blocks(name, arch).values())
    assert all(names[n] >= 1 for n in needs), {n: names[n] for n in needs}
    assert names["cut_red_sandstone"] == names["chiseled_red_sandstone"] == 0
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


@pytest.mark.parametrize("arch", ["western", "middle_eastern", "mesoamerican"])
def test_other_wonders_have_no_cinnabar(arch):
    assert not any("cinnabar" in s for s in blocks("WONDER", arch).values())
