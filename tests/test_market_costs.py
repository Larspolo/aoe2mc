"""game/civs.py: the market bonuses of the Muisca and the Saracens (AoE2 DE, #2176): Caravan and Guilds are free for
the Muisca, and a Saracen market costs less wood."""
from urllib.parse import unquote

from test_civ_costs import setup

from game import build, train


def market(civ, **stock):
    """An Imperial Age player of civilization civ with a built market at blocks x 10-12, z 2-4, and its menu."""
    server, g = setup(civ, **stock)
    g.techs.update({"CASTLE_AGE", "IMPERIAL_AGE"})
    g.sites[-1]["name"] = "MARKET"
    rect = train.open_menu(g, "Steve", (11, 3))
    return server, g, rect, [unquote(c) for c in server.log if c.startswith("aoe menu ")][-1]


def test_caravan_and_guilds_are_free_for_the_muisca():
    _, g, rect, menu = market("MUISCA")
    assert ":book:Caravan:free · " in menu and ":book:Guilds:free · " in menu
    assert train.order(g, "Steve", rect, train.SLOTS["CARAVAN"]) == 1 and train.order(g, "Steve", rect, train.SLOTS["GUILDS"]) == 1
    assert not any(g.stock.get(r) for r in ("food", "wood", "gold", "stone"))


def test_other_civilizations_pay_for_caravan_and_guilds():
    _, g, rect, menu = market("GOTHS", food=5000, gold=5000)
    assert ":book:Caravan:free · " not in menu and ":book:Guilds:free · " not in menu
    cost = train.price(g, "CARAVAN")
    assert cost and train.order(g, "Steve", rect, train.SLOTS["CARAVAN"]) == 1
    assert (g.stock["food"], g.stock["gold"]) == (5000 - cost.get("food", 0), 5000 - cost.get("gold", 0))


def test_a_saracen_market_costs_less_wood():
    _, g = setup("SARACENS")
    wood = build.price(g, "MARKET")["wood"]
    assert wood < build.COSTS["MARKET"]["wood"]
    g.stock["wood"] = wood
    assert next(lore for _, _, name, lore in build.items(g) if name == "Market").startswith(f"{wood} wood\n")
    site = build.found(g, "MARKET", (14, 18, 14, 18))
    assert site["name"] == "MARKET" and g.stock["wood"] == 0
    _, g = setup("MUISCA")
    assert build.price(g, "MARKET") == build.COSTS["MARKET"]
