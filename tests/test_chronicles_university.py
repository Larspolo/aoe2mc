"""The naval technologies of the university (#2136, AoE2 DE wiki, The Last Chieftains): Clinker Construction (Castle
Age, 150 food 100 wood, 50 s) and Carvel Hull (Imperial Age, 150 food 100 wood, 60 s) make the ships 10 % faster each;
Siphons (Castle Age, 100 food 175 gold, 45 s) and Incendiaries (Imperial Age, 100 food 175 gold, 50 s). The wiki
availability charts give the civilizations without them (civs.MISSING). Fake server."""
import pytest
from test_shipwright import imperial
from test_train_archery import menus

from game import fleet, train

WIKI = {"CLINKER_CONSTRUCTION": ({"food": 150, "wood": 100}, 50, 2, None),
        "CARVEL_HULL": ({"food": 150, "wood": 100}, 60, 3, "CLINKER_CONSTRUCTION"),
        "SIPHONS": ({"food": 100, "gold": 175}, 45, 2, None),
        "INCENDIARIES": ({"food": 100, "gold": 175}, 50, 3, "SIPHONS")}


def test_the_cost_time_and_age_are_those_of_aoe2():
    for name, (cost, time, age, after) in WIKI.items():
        assert name in train.TRAINS["UNIVERSITY"] and train.HELP[name], name
        assert train.COSTS[name] == cost and train.TRAIN_TIMES[name] == time and train.TECH_AGE[name] == age, name
        assert train.AFTER.get(name) == after, name


def test_a_civilization_with_it_sees_it_one_without_it_does_not():
    server, g = imperial("BRITONS")
    assert all(train.unlocked(g, n) for n in ("CLINKER_CONSTRUCTION", "SIPHONS"))
    assert not train.unlocked(g, "INCENDIARIES")                       # the chart: Default 0, no Britons
    server, g = imperial("ITALIANS", techs=("SIPHONS",))
    assert train.unlocked(g, "INCENDIARIES")
    server, g = imperial("SAXONS")
    assert not train.unlocked(g, "CLINKER_CONSTRUCTION") and train.unlocked(g, "SIPHONS")   # "All except Saxons"
    server, g = imperial("AZTECS", techs=("CLINKER_CONSTRUCTION",))
    assert not train.unlocked(g, "CARVEL_HULL") and not train.unlocked(g, "SIPHONS")


def test_the_university_menu_has_them_in_their_age():
    server, g = imperial("KOREANS")                                    # the Italians pay 25 % less
    g.techs -= {"IMPERIAL_AGE"}
    train.open_menu(g, "Steve", (8, 18))
    menu = menus(server)[-1]
    assert "23:book:Clinker Construction:150 food · 100 wood · 50 s" in menu
    assert "24:book:Siphons:100 food · 175 gold · 45 s" in menu
    assert "Carvel Hull" not in menu and "Incendiaries" not in menu
    g.techs |= {"IMPERIAL_AGE", "CLINKER_CONSTRUCTION", "SIPHONS"}
    train.open_menu(g, "Steve", (8, 18))
    menu = menus(server)[-1]
    assert "23:book:Carvel Hull:150 food · 100 wood · 60 s" in menu and "24:book:Incendiaries:" in menu


def test_each_one_makes_the_live_and_the_new_ships_10_percent_faster():
    server, g = imperial()
    g.soldiers["boat"] = "GALLEY"                                      # a live ship
    g.stock.update(food=300, wood=200)
    before = {n: fleet.speed(n, g.map.T, g) for n in ("GALLEY", "TRANSPORT_SHIP", "TRADE_COG", "FISHING_SHIP")}
    rect = train.open_menu(g, "Steve", (8, 18))
    assert train.order(g, "Steve", rect, 23) == 1
    server.log.clear()
    train.tick(g, 50.1)
    assert "CLINKER_CONSTRUCTION" in g.techs
    assert not any(c.startswith("attribute boat ") for c in server.log)   # a boat: fleet.tick reads the speed
    for n, v in before.items():
        assert fleet.speed(n, g.map.T, g) == pytest.approx(v * 1.1), n
    assert train.speed(g, "MILITIA") == train.speed(g, "VILLAGER_MALE") == 1
    rect = train.open_menu(g, "Steve", (8, 18))
    assert train.order(g, "Steve", rect, 23) == 1                      # now Carvel Hull in the same slot
    train.tick(g, 60.1)
    assert "CARVEL_HULL" in g.techs and fleet.speed("GALLEY", g.map.T, g) == pytest.approx(before["GALLEY"] * 1.21)
