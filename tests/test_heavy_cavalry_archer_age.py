"""game/build.py: the heavy cavalry archer is an Imperial Age unit, as in AoE2 DE (wiki infobox `Age`, #1429)."""
from game import build


def test_the_heavy_cavalry_archer_is_an_imperial_age_unit():
    assert build.AGE["HEAVY_CAVALRY_ARCHER"] == 3
