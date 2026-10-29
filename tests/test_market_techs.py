"""game/train.py: the market researches Caravan (Castle Age: trade carts walk faster) and Guilds (Imperial Age: a lower
trading fee), as on the AoE2 wiki infoboxes (#1254). Coinage and Banking change the tribute fee:
tests/test_coinage_banking.py (#1606)."""
from menu_line import item
from test_loom import menus
from test_trade_cart import FAR, HOME, setup

from game import ai, build, gather, market, trade, train


def market_map(age, **stock):
    server, g = setup()
    g.techs |= set(build.AGE_TECHS[:age])
    g.stock.update(stock)
    return server, g


def research(g, name):
    """Research name at the market with just its cost."""
    g.stock.update(train.price(g, name))
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (3, 3)), train.SLOTS[name]) == 1
    assert g.stock["food"] == g.stock["gold"] == 0
    train.tick(g, train.seconds(g, name, "MARKET") - 1)
    assert not g.techs & {"CARAVAN", "GUILDS"}
    train.tick(g, 1)


def test_the_market_menu_shows_each_technology_from_its_age():
    for age, shown in ((1, ()), (2, ("Caravan",)), (3, ("Caravan", "Guilds"))):
        server, g = market_map(age)
        train.open_menu(g, "Steve", (3, 3))
        assert [n for n in ("Caravan", "Guilds") if f":book:{n}:" in menus(server)[-1]] == list(shown)
    assert all(item(menus(server)[-1], n).endswith(" · research") for n in ("Caravan", "Guilds"))


def test_caravan_makes_the_trade_carts_walk_faster():
    server, g = market_map(2, food=0, gold=0)
    assert train.speed(g, "TRADE_CART") == 1
    research(g, "CARAVAN")
    faster = train.speed(g, "TRADE_CART")
    assert "CARAVAN" in g.techs and faster > 1 and train.speed(g, "MONK") == 1
    g.selected = {"c"}
    server.log.clear()
    assert market.fee(g) == market.FEE and trade.order(g, "Steve", (19, 17)) == FAR
    fast = ai.speed_command("c", "TRADE_CART", g.map.T, gather.NORMAL * faster)
    assert fast in server.log and fast != ai.speed_command("c", "TRADE_CART", g.map.T, gather.NORMAL)


def test_guilds_lowers_the_trading_fee():
    server, g = market_map(3, food=0, gold=0)
    buy, sell = market.price(g, "wood", True), market.price(g, "wood", False)
    assert market.fee(g) == market.FEE
    research(g, "GUILDS")
    assert "GUILDS" in g.techs and market.fee(g) == market.FEES["GUILDS"] < market.FEE
    assert market.price(g, "wood", True) < buy and market.price(g, "wood", False) > sell
    assert train.open_menu(g, "Steve", (3, 3)) == HOME and ":Guilds:" not in menus(server)[-1]   # once only

