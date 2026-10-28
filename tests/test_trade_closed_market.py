"""game/trade.py: a trade cart whose next market has no free door ends its route, so it pays no gold for a walk it did not make."""
from test_trade_cart import FAR, HOME, moves, setup

from game import trade


def test_a_cart_whose_far_market_is_walled_in_pays_once_and_ends_its_route():
    server, g = setup()
    g.selected = {"c"}
    assert trade.order(g, "Steve", (19, 17)) == FAR
    server.entities["c"]["Pos"] = moves(server, "c")[-1]
    trade.tick(g)                                                      # at the far door: out, home
    g.map.blocked |= {(x, z) for x in range(15, 24) for z in range(13, 22)}   # walls close the far market in
    server.entities["c"]["Pos"] = moves(server, "c")[-1]
    trade.tick(g)                                                      # at home: the gold of the trip, then no door
    one = trade.gold(trade.center(HOME, 1), trade.center(FAR, 1), 24)
    assert g.stock["gold"] == int(one) and "c" not in g.trade
    for _ in range(10):
        trade.tick(g)
    assert g.stock["gold"] == int(one)
