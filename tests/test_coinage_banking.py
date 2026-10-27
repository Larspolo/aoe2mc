"""Coinage and Banking (#1606): the market researches Coinage (200 food, 100 gold, 70 s, Castle Age: tribute fee 20 %)
and, after it, Banking (300 food, 200 gold, 70 s, Imperial Age: tributes are free), as on the AoE2 wiki infoboxes."""
from test_loom import menus
from test_market_techs import market_map
from test_tribute import setup

from game import diplomacy, train


def test_the_costs_times_and_ages_are_those_of_aoe2():
    assert train.COSTS["COINAGE"] == {"food": 200, "gold": 100} and train.TRAIN_TIMES["COINAGE"] == 70
    assert train.COSTS["BANKING"] == {"food": 300, "gold": 200} and train.TRAIN_TIMES["BANKING"] == 70
    assert train.TECH_AGE["COINAGE"] == 2 and train.TECH_AGE["BANKING"] == 3 and train.AFTER["BANKING"] == "COINAGE"
    assert all(len(train.HELP[t]) <= 50 for t in ("COINAGE", "BANKING"))


def test_the_market_shows_coinage_in_the_castle_age_and_banking_after_it():
    server, g = market_map(1)
    train.open_menu(g, "Steve", (3, 3))
    assert ":Coinage:" not in menus(server)[-1]
    server, g = market_map(3, food=200, gold=100)
    train.open_menu(g, "Steve", (3, 3))
    assert "3:book:Coinage:200 food · 100 gold · 70 s · research" in menus(server)[-1]
    assert ":Banking:" not in menus(server)[-1]
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (3, 3)), 3) == 1
    train.tick(g, 70)
    assert "COINAGE" in g.techs
    train.open_menu(g, "Steve", (3, 3))
    assert "3:book:Banking:300 food · 200 gold · 70 s · research" in menus(server)[-1]
    g.stock.update(food=300, gold=200)
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (3, 3)), 3) == 1
    train.tick(g, 70)
    assert "BANKING" in g.techs


def test_the_fee_of_a_tribute_of_100_is_30_then_20_then_0():
    server, g = setup()
    fees = []
    for tech in ((), ("COINAGE",), ("BANKING",)):
        g.techs |= set(tech)
        fees.append(diplomacy.cost(g, 100) - 100)
    assert fees == [30, 20, 0]
    g.stock["food"] = 100
    assert diplomacy.order(g, "Steve", 9) == 1 and g.stock["food"] == 0   # with Banking: 100 food sends 100
    page = diplomacy.items(g)
    assert any(t == "100 food with the fee" for *_, t in page)
