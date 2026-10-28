"""game/trade.py, fleet.py, repair.py: a new order ends the trade route of a cart, and the trade and Serjeant orders
end the old orders of their units (Gather.new_order, #3278). Fake servers."""
from test_new_order_ends_old import TC, setup

from game import repair, trade

HOME, FAR = (2, 5, 2, 5), (16, 19, 16, 19)


def cart(g, rest=0.0):
    """Cart c with a route from HOME to FAR, next leg point (10, 10)."""
    g.soldiers["c"] = "TRADE_CART"
    g.trade["c"] = {"home": HOME, "market": FAR, "to": FAR, "cell": (17, 15), "legs": [(10, 10), (17, 15)],
                    "rest": rest}


def test_a_move_order_ends_the_trade_route():
    server, g = setup()
    cart(g)
    g.walk_to("Steve", (10, 11), units={"c"})
    assert "c" not in g.trade


def test_a_new_trade_order_keeps_the_gold_fraction(monkeypatch):
    server, g = setup()
    cart(g, rest=0.75)
    monkeypatch.setattr(trade, "markets", lambda g: [HOME, FAR])
    monkeypatch.setattr(trade, "walk", lambda g, u, rect, pos: [(17, 15)])
    monkeypatch.setattr(g, "positions", lambda us: {u: (6.5, 64.0, 9.5) for u in us})
    g.selected = {"c"}
    assert trade.order(g, "Steve", (17, 17)) == FAR
    assert g.trade["c"]["rest"] == 0.75 and g.trade["c"]["legs"] == [(17, 15)]


def test_a_donjon_build_order_ends_the_garrison_order(monkeypatch):
    server, g = setup()
    g.soldiers["s"] = "SERJEANT"
    g.entering = {"s": TC}
    site = {"name": "DONJON", "footprint": (10, 13, 10, 13), "progress": 0.2, "player": g.player}
    monkeypatch.setattr(repair, "march", lambda *a, **k: None)
    assert repair.build_order(g, site, {"s"}) == ["s"]
    assert "s" not in g.entering
