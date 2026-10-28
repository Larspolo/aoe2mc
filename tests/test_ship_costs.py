"""The ship cost bonuses of five civilizations (#2291, epic #1088; AoE2 DE wiki, civilization bonuses): Italian fishing
ships 15 % cheaper, Korean warships -20 % wood, Viking warships -10/15/20 % in the Feudal/Castle/Imperial Age, Malay
fish traps 33 % cheaper, and the free Careening and Dry Dock of the Wu."""
from test_loom import setup

from game import build, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def player(civ, age=0):
    _, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.update(AGES[:age])
    return g


def test_italian_fishing_ships_are_15_percent_cheaper():
    assert train.price(player("ITALIANS"), "FISHING_SHIP") == {"wood": 64}           # 75 × 0.85
    assert train.price(player("ITALIANS"), "TRANSPORT_SHIP") == {"wood": 125}


def test_korean_warships_cost_20_percent_less_wood():
    assert train.price(player("KOREANS", 1), "GALLEY") == {"wood": 72, "gold": 30}
    assert train.price(player("KOREANS", 1), "FISHING_SHIP") == {"wood": 75}           # no warship


def test_viking_warships_are_cheaper_in_each_age():
    assert train.price(player("VIKINGS"), "GALLEY") == {"wood": 90, "gold": 30}       # the Dark Age: no bonus
    assert train.price(player("VIKINGS", 1), "GALLEY") == {"wood": 81, "gold": 27}
    assert train.price(player("VIKINGS", 2), "GALLEY") == {"wood": 77, "gold": 26}    # 76.5 and 25.5 round up
    assert train.price(player("VIKINGS", 3), "GALLEY") == {"wood": 72, "gold": 24}
    assert train.price(player("VIKINGS", 3), "FISHING_SHIP") == {"wood": 75}


def test_malay_fish_traps_are_33_percent_cheaper():
    assert build.price(player("MALAY"), "FISH_TRAP") == {"wood": 67}
    assert build.price(player("BRITONS"), "FISH_TRAP") == {"wood": 100}


def test_careening_and_dry_dock_are_free_for_the_wu():
    for t in ("CAREENING", "DRY_DOCK"):
        assert not any(train.price(player("WU"), t).values())
        assert train.price(player("BRITONS"), t) == train.COSTS[t]


def test_other_civilizations_pay_the_base_cost():
    for name in ("GALLEY", "FISHING_SHIP"):
        assert train.price(player("BRITONS", 3), name) == train.COSTS[name]
