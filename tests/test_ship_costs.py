"""The ship cost bonuses of the civilizations (#2291, epic #1088; AoE2 DE wiki, civilization bonuses): a civilization
with no ship bonus pays the base cost in the Imperial Age."""
from test_loom import setup

from game import train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def player(civ, age=0):
    _, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.update(AGES[:age])
    return g


def test_other_civilizations_pay_the_base_cost():
    for name in ("GALLEY", "FISHING_SHIP"):
        assert train.price(player("BRITONS", 3), name) == train.COSTS[name]
