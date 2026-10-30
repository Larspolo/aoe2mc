"""A complete building gives the food of BUILT_FOOD in game/data/civs.jsonl once (#2114: Saxon camps and mills, Wu
military buildings and docks). Fake server."""
import pytest
from test_treadmill_crane import castle

from game import build, civs


def food_of(civ, name):
    """The food that a complete site of name of civ gives, and the food of one more rise after it."""
    server, g = castle(civ)
    site, food = build.found(g, name, (12, 14, 8, 10)), g.stock["food"]
    assert build.rise(g, site, build.BUILD_TIMES[name])
    after = g.stock["food"]
    build.rise(g, site, 1.0)
    return after - food, g.stock["food"] - after


@pytest.mark.parametrize("civ, name", [("SAXONS", "MILL"), ("SAXONS", "LUMBER_CAMP"), ("SAXONS", "MINING_CAMP"),
                                       ("WU", "STABLE"), ("WU", "BARRACKS"), ("WU", "DOCK"), ("SAXONS", "HOUSE"),
                                       ("SAXONS", "STABLE"), ("WU", "MILL"), ("BRITONS", "MILL"), ("BRITONS", "STABLE")])
def test_a_complete_building_gives_its_food_once(civ, name):
    assert food_of(civ, name) == (civs.BUILT_FOOD.get(civ, {}).get(name, 0), 0)


def test_the_names_are_buildings():
    assert {n for b in civs.BUILT_FOOD.values() for n in b} <= set(build.BUILD_TIMES)
