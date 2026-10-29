"""game/trade.py: the market trains a trade cart (AoE2 DE), and a trade cart walks
between two own markets and brings the gold of the AoE2 formula to its home market (#1253)."""
import re

import pytest
from test_gather import FakeServer, grid
from test_loom import menus

import units
from game import build, combat, gather, trade, train

HOME, FAR = (2, 5, 2, 5), (18, 21, 16, 19)                             # block footprints (x0, x1, z0, z1)


def setup(wood=0, gold=0):
    """A flat 24 × 24 map (tile size 1) with two complete own markets, a house (population room) and an own trade cart "c"
    near HOME."""
    objects = [{"kind": "building", "name": "MARKET", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "MARKET", "player": 1, "tile": [19.5, 17.5], "footprint": [18, 16, 21, 19]},
               {"kind": "building", "name": "HOUSE", "player": 1, "tile": [11.0, 11.0], "footprint": [10, 10, 12, 12]},
               {"kind": "unit", "name": "TRADE_CART_EMPTY", "player": 1, "uuid": "c", "tile": [3.5, 8.5]}]
    server = FakeServer({"c": {"Pos": (3.5, 64.0, 8.5)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    g.techs |= set(build.AGE_TECHS[:1])                                # the Feudal Age
    g.stock.update(wood=wood, gold=gold)
    return server, g


def moves(server, uuid):
    return [tuple(map(float, c.split()[3:])) for c in server.log if c.startswith(f"aoe moveto {uuid} ")]


def test_the_market_menu_trains_a_trade_cart_with_its_cost_and_time():
    cost = train.COSTS["TRADE_CART"]
    server, g = setup(wood=cost.get("wood", 0), gold=cost.get("gold", 0) + 10)
    rect = train.open_menu(g, "Steve", (3, 3))
    slot, _, label = train.layout(g, rect)["TRADE_CART"]
    assert rect == HOME and f":{label}:" in menus(server)[-1]
    assert train.order(g, "Steve", rect, slot) == 1 and (g.stock["wood"], g.stock["gold"]) == (0, 10)
    assert train.tick(g, train.TRAIN_TIMES["TRADE_CART"] - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(rf"summon {units.classify('TRADE_CART')['id']} ", summon)
    assert g.soldiers[uuid] == "TRADE_CART" and uuid not in g.villagers   # a cart does not gather


def test_the_gold_of_a_trip_follows_the_aoe2_formula():
    # d = 25 tiles after 5 free tiles on each axis, map of 120 tiles: 0.46 * 25 * (25 / 120 + 0.3)
    assert trade.gold((10, 50), (40, 50), 120) == pytest.approx(0.46 * 25 * (25 / 120 + 0.3))
    # d = sqrt(40² + 60²) on a map of 200 tiles
    d = (40 ** 2 + 60 ** 2) ** 0.5
    assert trade.gold((5, 5), (50, 70), 200) == pytest.approx(0.46 * d * (d / 200 + 0.3))
    # the wiki maximum: markets in the corners of a ludicrous map (480 tiles) give 517 gold
    assert round(trade.gold((2, 2), (478, 478), 480)) == 517
    assert trade.gold((5, 5), (9, 8), 120) == pytest.approx(0.46 * 0.1 * (0.1 / 120 + 0.3))   # nearer than 5 tiles


def test_a_cart_walks_to_the_far_market_and_back_and_brings_the_gold_home():
    server, g = setup()
    g.selected = {"c"}
    assert trade.order(g, "Steve", (19, 17)) == FAR
    door = moves(server, "c")[-1]
    assert FAR[0] <= door[0] <= FAR[1] and door[2] == FAR[3] + 0.5   # the door cell on the south side
    trade.tick(g)
    assert len(moves(server, "c")) == 1                               # not there yet: no new order
    server.entities["c"]["Pos"] = door
    trade.tick(g)
    home = moves(server, "c")[-1]
    assert HOME[0] <= home[0] <= HOME[1] and home[2] == HOME[3] + 0.5 and g.stock["gold"] == 0
    one = trade.gold(trade.center(HOME, 1), trade.center(FAR, 1), 24)
    for trip in (1, 2):
        server.entities["c"]["Pos"] = home
        trade.tick(g)                                                  # at home: the gold, then out again
        assert g.stock["gold"] == int(trip * one) and moves(server, "c")[-1] == door
        server.entities["c"]["Pos"] = door
        trade.tick(g)
    assert sum(int(c.split()[-1]) for c in server.log if c.startswith("scoreboard players add Gold ")) == int(2 * one)


def test_no_trade_order_without_a_second_market_or_a_selected_cart():
    server, g = setup()
    assert trade.order(g, "Steve", (19, 17)) is None                  # nothing selected
    g.selected = {"c"}
    assert trade.order(g, "Steve", (10, 10)) is None                  # no market there
    g.data["objects"] = [o for o in g.data["objects"] if o.get("tile") != [19.5, 17.5]]
    assert trade.order(g, "Steve", (3, 3)) is None and not g.trade    # one market only


@pytest.mark.mc
def test_a_trade_cart_makes_one_trip_on_a_server(tmp_path):
    """A trained trade cart walks with the plugin to a second own market and back, and brings the gold of the formula."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo

    from game import run
    scn = scenarios.new_scenario(32)
    for x, y in ((7, 7), (21, 21)):
        scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.MARKET.ID, x=x, y=y)
    src = str(tmp_path / "t.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, tick=0.25).setup()
        home, far = trade.markets(g)
        x, z = g.map.front(home)[0]
        cart = train.summon(g, "TRADE_CART", (x + 0.5, float(g.map.y(x, z)), z + 0.5))
        g.choose({cart}, cart)
        assert trade.order(g, "nobody", (far[0], far[2])) == far and g.trade[cart]["home"] == home
        one = trade.gold(trade.center(home, g.map.T), trade.center(far, g.map.T), g.map.n / g.map.T)
        start, end = g.stock["gold"], time.time() + 180
        seen = set()
        while g.stock["gold"] == start:
            assert time.time() < end, (g.pos(cart), g.trade)
            g.step()
            seen.add(g.trade[cart]["to"])
            time.sleep(g.tick)
        assert seen == {home, far} and g.stock["gold"] - start == int(one) > 0
