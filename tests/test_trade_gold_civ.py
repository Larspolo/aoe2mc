"""The civilization factor "trade_gold" (data/civs.jsonl, Palmyrans +20 %, #4446) multiplies the gold of each trade trip
of a trade cog. The test changes the factor of the civilization of the docks (BRITONS) with a patch of civs.BY_KEY."""
import pytest
from test_trade_cog import FAR, TIME, docks_map

import civs
from game import fleet, train


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


def test_a_trade_cog_brings_the_trade_gold_factor_of_its_civilization(monkeypatch):
    base = cog_gold()
    assert base > 0
    monkeypatch.setitem(civs.BY_KEY, "trade_gold", {"BRITONS": 1.2})
    assert cog_gold() == pytest.approx(1.2 * base)
