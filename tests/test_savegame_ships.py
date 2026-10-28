"""game/savegame.py: a save keeps the orders of the ships, the routes of the trade carts and the state of the
trebuchets (#2413, epic #2253). Fake server, no Minecraft."""
import json

from test_ship_gather import fish_map

from game import fleet, savegame, trebuchet

HOME, FAR = (2, 5, 2, 5), (8, 11, 18, 21)                              # market footprints (x0, x1, z0, z1)
ROUTE = {"home": HOME, "market": FAR, "to": FAR, "cell": (9, 17), "legs": [(6, 10), (9, 17)], "rest": 0.5}


def played():
    """A fishing ship that sails to the water cell (20, 5), a trade cart "c" on its route to the far market and an
    unpacked trebuchet "t"."""
    server, g, ship = fish_map()
    assert fleet.order(g, [ship], (20, 5)) == {ship: (20, 5)}
    g.soldiers["c"], g.trade["c"] = "TRADE_CART_EMPTY", {k: list(v) if k == "legs" else v for k, v in ROUTE.items()}
    g.soldiers["t"] = "TREBUCHET"
    g.trebs = {"t": ["unpacked", 0.0, []]}
    return g, ship


def loaded(g):
    server, h, _ = fish_map()
    h.soldiers["c"], h.soldiers["t"] = "TRADE_CART_EMPTY", "TREBUCHET"
    server.log.clear()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def test_a_loaded_game_has_the_ship_order_the_trade_route_and_the_trebuchet_state():
    g, ship = played()
    server, h = loaded(g)
    a, b = g.ships[ship], h.ships[ship]
    assert (b.state, b.pos, b.path[-1]) == (a.state, a.pos, (20, 5))   # a new water path to the same goal
    assert h.trade["c"] == ROUTE | {"legs": [(6, 10), (9, 17)]}
    assert any(c.startswith("aoe moveto c 6.5 ") for c in server.log)   # the cart walks on with its leg
    assert trebuchet.state(h, "t") == "unpacked"


def test_a_walking_trebuchet_walks_on():
    g, _ = played()
    g.trebs["t"] = ["walking", 0.0, ["enemy", (10.5, 64.0, 10.5)]]
    server, h = loaded(g)
    assert h.trebs["t"] == ["walking", 0.0, ["enemy", (10.5, 64.0, 10.5)]]
    assert "aoe moveto t 10.5 64.0 10.5" in server.log


def test_a_save_from_before_the_ships_still_loads():
    g, ship = played()
    d = savegame.dump(g)
    for k in ("ships", "trade", "trebs"):
        del d["players"]["1"][k]
    _, h, _ = fish_map()
    savegame.load(h, d)
    assert h.stock == g.stock and "trebs" not in vars(h) and not h.trade
