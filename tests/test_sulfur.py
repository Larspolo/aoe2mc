"""The Sankore Madrasah has yellow ochre trim of sulfur stone (#556)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc


def test_sankore_trim_is_sulfur():
    names = Counter(s.split("[")[0] for s in blocks("SANKORE_MADRASAH", "african").values())
    assert all(names[n] >= 1 for n in ("polished_sulfur", "chiseled_sulfur", "sulfur_bricks", "polished_sulfur_wall"))
    sulfur = sum(v for k, v in names.items() if "sulfur" in k)
    assert names["mud_bricks"] > 3 * sulfur                                  # the mud brick stays the majority
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


@pytest.mark.parametrize("name,arch", [("WONDER", "african"), ("HOUSE", "african"), ("CASTLE", "middle_eastern")])
def test_other_designs_have_no_sulfur(name, arch):
    assert not any("sulfur" in s for s in blocks(name, arch).values())
