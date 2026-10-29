"""Coinage and Banking (#1606): the market researches Coinage (Castle Age: a lower tribute fee) and, after it, Banking
(Imperial Age: tributes are free), as on the AoE2 wiki infoboxes."""
from test_castle_upgrades import entry
from test_loom import menus
from test_market_techs import market_map
from test_tribute import setup

from game import diplomacy, train


def test_the_help_texts_are_short():
    assert all(len(train.HELP[t]) <= 50 for t in ("COINAGE", "BANKING"))


def test_the_market_shows_coinage_in_the_castle_age_and_banking_after_it():
    server, g = market_map(1)
    train.open_menu(g, "Steve", (3, 3))
    assert ":Coinage:" not in menus(server)[-1]
    server, g = market_map(3, food=10000, gold=10000)
    train.open_menu(g, "Steve", (3, 3))
    assert entry(g, (3, 3), "COINAGE") + "research" in menus(server)[-1]
    assert ":Banking:" not in menus(server)[-1]
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.layout(g, rect)["COINAGE"][0]) == 1
    train.tick(g, train.seconds(g, "COINAGE"))
    assert "COINAGE" in g.techs
    train.open_menu(g, "Steve", (3, 3))
    assert entry(g, (3, 3), "BANKING") + "research" in menus(server)[-1]
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.layout(g, rect)["BANKING"][0]) == 1
    train.tick(g, train.seconds(g, "BANKING"))
    assert "BANKING" in g.techs


def test_the_fee_of_a_tribute_is_lower_after_coinage_and_after_banking():
    server, g = setup()
    fees = []
    for tech in ((), ("COINAGE",), ("BANKING",)):
        g.techs |= set(tech)
        fees.append(diplomacy.cost(g, 100) - 100)
    assert fees[0] > fees[1] > fees[2] >= 0, fees
    g.stock["food"] = diplomacy.cost(g, 100)
    assert diplomacy.order(g, "Steve", 9) == 1 and g.stock["food"] == 0   # with Banking: 100 food and its fee
    page = diplomacy.items(g)
    assert any(t == "100 food with the fee" for *_, t in page)
