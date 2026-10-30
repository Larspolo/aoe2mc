"""The civilization factor "trade_gold" (data/civs.jsonl, Palmyrans +20 %, #4446) multiplies the gold of each trade trip
of a trade cart and a trade cog, not the relic gold. The tests change the factor with a patch of civs.BY_KEY."""
import pytest
import test_relics
import test_trade_cart
from test_trade_cog import FAR, TIME, docks_map

import civs
from game import fleet, monk, trade, train


def cog_gold():
    """The gold of the trade cog after 200 ticks of a route between the two docks: the stock and the fraction kept."""
    server, g = docks_map()
    train.order(g, "Steve", train.open_menu(g, "Steve", (15, 3)), train.MORE)
    cog, = train.tick(g, TIME)
    g.selected = {cog}
    assert fleet.trade_order(g, "Steve", (15, 33)) == FAR
    for _ in range(200):
        fleet.tick(g, 0.5)
    return g.stock["gold"] + g.ships[cog].route["rest"]


def cart_gold():
    """The gold of the trade cart after one trip to the far market and back: the stock and the fraction kept."""
    server, g = test_trade_cart.setup()
    g.selected = {"c"}
    trade.order(g, "Steve", (19, 17))
    server.entities["c"]["Pos"] = test_trade_cart.moves(server, "c")[-1]   # at the far market
    trade.tick(g)
    server.entities["c"]["Pos"] = test_trade_cart.moves(server, "c")[-1]   # back at home
    trade.tick(g)
    return g.stock["gold"] + g.trade["c"]["rest"]


def relic_gold():
    """The gold of one relic in the monastery after 60 relic passes: the stock and the fraction kept."""
    server, g = test_relics.setup()
    g.relics[0].update(at=None, home=(14, 18, 2, 6))
    for _ in range(60):
        monk.relic_tick(g, monk.EVERY)
    return g.stock["gold"] + g.relic_gold


def test_a_trade_cog_brings_the_trade_gold_factor_of_its_civilization(monkeypatch):
    base = cog_gold()
    assert base > 0
    monkeypatch.setitem(civs.BY_KEY, "trade_gold", {"BRITONS": 1.2})
    assert cog_gold() == pytest.approx(1.2 * base)


def test_a_trade_cart_brings_the_factor_and_a_relic_does_not(monkeypatch):
    cart, relic = cart_gold(), relic_gold()
    assert cart > 0 and relic > 0
    monkeypatch.setattr(civs, "civ", lambda g, player=None: "TEST")
    monkeypatch.setitem(civs.BY_KEY, "trade_gold", {"TEST": 1.2})
    assert cart_gold() == pytest.approx(1.2 * cart)
    assert relic_gold() == pytest.approx(relic)
