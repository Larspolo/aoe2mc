"""Saxon mills, lumber camps and mining camps give 35 food when complete, Wu military buildings and docks 55 food
(#2114, AoE2 DE wiki): BUILT_FOOD in game/data/civs.jsonl. Fake server."""
import pytest

from game import build, civs
from test_treadmill_crane import castle


def food_of(civ, name):
    """The food that a complete site of name of civ gives, and the food of one more rise after it."""
    server, g = castle(civ)
    site, food = build.found(g, name, (12, 14, 8, 10)), g.stock["food"]
    assert build.rise(g, site, build.BUILD_TIMES[name])
    after = g.stock["food"]
    build.rise(g, site, 1.0)
    return after - food, g.stock["food"] - after


@pytest.mark.parametrize("civ, name, food", [("SAXONS", "MILL", 35), ("SAXONS", "LUMBER_CAMP", 35),
                                             ("SAXONS", "MINING_CAMP", 35), ("WU", "STABLE", 55),
                                             ("WU", "BARRACKS", 55), ("WU", "DOCK", 55)])
def test_a_complete_building_gives_food_once(civ, name, food):
    assert food_of(civ, name) == (food, 0)


@pytest.mark.parametrize("civ, name", [("SAXONS", "HOUSE"), ("SAXONS", "STABLE"), ("WU", "MILL"), ("BRITONS", "MILL"),
                                       ("BRITONS", "STABLE")])
def test_other_buildings_and_civilizations_give_no_food(civ, name):
    assert food_of(civ, name) == (0, 0)


def test_the_names_are_buildings():
    assert {n for b in civs.BUILT_FOOD.values() for n in b} <= set(build.BUILD_TIMES)
