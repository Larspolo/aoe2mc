"""game/civs.py COSTS: the civilization cost bonuses of the economic technologies also cover the Castle Age ones of
#1423 (Bow Saw, Gold Shaft Mining, Stone Shaft Mining), as in AoE2 DE (AoE2 wiki, MediaWiki API, 2026-10-27: the
"Boosts" table of each page and the civilization pages): Burmese and Bohemians free, Vietnamese no wood, Burgundians
-40 % food, Chinese -10 % in the Castle Age (#1447)."""
import types

import pytest

from game import civs, train

CASTLE = {"FEUDAL_AGE", "CASTLE_AGE"}


def cost(civ, name, ages=CASTLE):
    g = types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(ages))
    return civs.cost(g, name, train.COSTS[name])


@pytest.mark.parametrize("civ, name, want", [
    ("BURMESE", "BOW_SAW", {}),
    ("BOHEMIANS", "GOLD_SHAFT_MINING", {}),
    ("BOHEMIANS", "STONE_SHAFT_MINING", {}),
    ("VIETNAMESE", "BOW_SAW", {"food": 150}),
    ("VIETNAMESE", "GOLD_SHAFT_MINING", {"food": 175}),               # the civilization page: all economic ones
    ("VIETNAMESE", "STONE_SHAFT_MINING", {"food": 175}),
    ("BURGUNDIANS", "BOW_SAW", {"food": 90, "wood": 100}),
    ("BURGUNDIANS", "GOLD_SHAFT_MINING", {"food": 105, "wood": 75}),
    ("BURGUNDIANS", "STONE_SHAFT_MINING", {"food": 105, "wood": 75}),
    ("CHINESE", "BOW_SAW", {"food": 135, "wood": 90}),
    ("BRITONS", "BOW_SAW", {"food": 150, "wood": 100}),               # no bonus
    ("BURMESE", "GOLD_SHAFT_MINING", {"food": 175, "wood": 75}),
    ("BOHEMIANS", "BOW_SAW", {"food": 150, "wood": 100}),
])
def test_the_castle_age_gathering_technologies_cost_as_in_aoe2(civ, name, want):
    assert cost(civ, name) == want


def test_the_feudal_age_technologies_keep_their_bonuses():
    assert cost("BURMESE", "DOUBLE_BIT_AXE", {"FEUDAL_AGE"}) == {} and cost("BOHEMIANS", "GOLD_MINING") == {}
    assert cost("VIETNAMESE", "HORSE_COLLAR", {"FEUDAL_AGE"}) == {"food": 75}
    assert cost("BURGUNDIANS", "DOUBLE_BIT_AXE", {"FEUDAL_AGE"}) == {"food": 60, "wood": 50}
