"""game/trade.py: a trade cart walks a long way between two markets in legs of trade.LEG path cells, each within the
reach of one Minecraft path search (#1305: with one order the cart turned back after 125 of 170 blocks)."""
import math

import pytest
from test_gather import FakeServer, grid
from test_trade_cart import moves

from game import build, gather, trade

N = 220                                                                # blocks (tile size 1)
HOME, FAR = (2, 5, 2, 5), (200, 203, 200, 203)


def setup():
    objects = [{"kind": "building", "name": "MARKET", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "MARKET", "player": 1, "tile": [201.5, 201.5],
                "footprint": [200, 200, 203, 203]},
               {"kind": "unit", "name": "TRADE_CART_EMPTY", "player": 1, "uuid": "c", "tile": [3.5, 8.5]}]
    server = FakeServer({"c": {"Pos": (3.5, 64.0, 8.5)}})
    g = gather.Gather(server, grid([[64] * N for _ in range(N)], objects)).setup()
    g.paper = True
    g.techs |= set(build.AGE_TECHS[:1])
    return server, g


def test_a_long_way_goes_in_legs_and_brings_the_gold_home():
    server, g = setup()
    g.selected = {"c"}
    start = g.stock["gold"]
    assert trade.order(g, "Steve", (201, 201)) == FAR
    door = g.trade["c"]["cell"]
    assert FAR[0] <= door[0] < FAR[1] and door[1] == FAR[3]            # the door cell on the south side
    ends, pos = [], (3.5, 8.5)
    while g.trade["c"]["to"] == FAR and len(ends) < 20:                # the cart reaches the end of each leg
        ends.append(m := moves(server, "c")[-1])
        assert math.dist(pos, (m[0], m[2])) <= trade.LEG * math.sqrt(2) + 1   # within one path search
        pos = m[0], m[2]
        server.entities["c"]["Pos"] = m
        trade.tick(g)
    assert len(ends) >= 4 and (ends[-1][0], ends[-1][2]) == (door[0] + 0.5, door[1] + 0.5)
    assert g.trade["c"]["to"] == HOME and g.stock["gold"] == start     # out there: it turns home
    back = []
    while g.stock["gold"] == start and len(back) < 20:
        m = moves(server, "c")[-1]
        back.append(m)
        server.entities["c"]["Pos"] = m
        trade.tick(g)
    one = trade.gold(trade.center(HOME, 1), trade.center(FAR, 1), N)
    assert len(back) >= 4 and g.stock["gold"] - start == int(one) > 0


def test_a_leg_ends_near_its_cell_not_on_it():
    """The plugin walks the cart near the end of a leg (a path point of Minecraft): NEAR blocks start the next leg."""
    server, g = setup()
    g.selected = {"c"}
    trade.order(g, "Steve", (201, 201))
    first = moves(server, "c")[-1]
    server.entities["c"]["Pos"] = (first[0] - 2.0, first[1], first[2] - 1.5)
    trade.tick(g)
    assert moves(server, "c")[-1] != first


@pytest.mark.mc
def test_a_trade_cart_trades_between_markets_170_blocks_apart_on_a_server(tmp_path):
    """The scenario of #1305: 48 tiles, markets at tiles (8, 8) and (38, 38). With one order the cart turned back."""
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json
    import time

    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo

    import aoe2mc
    from game import combat, run, train
    scn = scenarios.new_scenario(48)
    for x, y in ((8, 8), (38, 38)):
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
        assert math.dist(trade.center(home, g.map.T), trade.center(far, g.map.T)) * g.map.T > 160
        x, z = g.map.front(home)[0]
        cart = train.summon(g, "TRADE_CART", (x + 0.5, float(g.map.y(x, z)), z + 0.5))
        g.choose({cart}, cart)
        assert trade.order(g, "nobody", (far[0], far[2])) == far and len(g.trade[cart]["legs"]) > 1
        one = trade.gold(trade.center(home, g.map.T), trade.center(far, g.map.T), g.map.n / g.map.T)
        start, end = g.stock["gold"], time.time() + 180
        seen = set()
        while g.stock["gold"] == start:
            assert time.time() < end, (g.pos(cart), g.trade)
            g.step()
            seen.add(g.trade[cart]["to"])
            time.sleep(g.tick)
        assert seen == {home, far} and g.stock["gold"] - start == int(one) > 0
