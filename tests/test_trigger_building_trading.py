"""#2868 (epic #2538): a trigger with the condition "Building Is Trading" fires in the scenario mode while a trade
cart trades with its market. The game program sets the score #r<ref> of aoe_trade (scenario.trading), and the tick
function of the datapack tests it."""
import contextlib
import io
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

from tools import scenarios  # noqa: E402

MARKET = {"kind": "building", "name": "MARKET", "player": 1, "ref": 12, "footprint": [2, 2, 6, 6]}
FAR = {"kind": "building", "name": "MARKET", "player": 1, "ref": 13, "footprint": [10, 10, 14, 14]}
DOCK = {"kind": "building", "name": "DOCK", "player": 2, "ref": 14, "footprint": [2, 10, 5, 13]}


def trig(ref=12, inverted=False):
    return dict(id=7, name="t", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.BUILDING_IS_TRADING, timer=0, inverted=inverted, ref=ref)],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Trade!", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def test_the_condition_tests_the_score_of_the_market_in_the_tick_function():
    load, files = aoe2mc.trigger_files([trig()])
    assert "execute if score #r12 aoe_trade matches 1 unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in files["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert "scoreboard objectives add aoe_trade dummy" in load


def test_an_inverted_condition_tests_the_score_0():
    tick = aoe2mc.trigger_files([trig(inverted=True)])[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "execute if score #r12 aoe_trade matches 0 unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in tick.splitlines()


def test_no_building_gives_no_trigger():
    assert aoe2mc.trigger_files([trig(ref=-1)])[1] == {}


def test_the_scenario_mode_sets_1_while_a_cart_trades_with_the_market():
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [MARKET, FAR, DOCK])).setup()
    g.bots = [types.SimpleNamespace(g=gather.Gather(server, grid([[64] * 16 for _ in range(16)], []), player=2))]
    scenario.trading(g)                                                # no cart: 0 for each, so inverted fires
    assert [c for c in server.log if " aoe_trade " in c] == ["scoreboard players set #r12 aoe_trade 0",
                                                             "scoreboard players set #r13 aoe_trade 0"]   # no dock
    # the route of trade.order: the cart walks to the far market and back home
    g.trade["cart"] = {"home": (10, 14, 10, 14), "market": (2, 6, 2, 6), "to": (2, 6, 2, 6), "cell": (4, 6),
                       "legs": [(4, 6)], "rest": 0.0}
    del server.log[:]
    scenario.trading(g)
    scenario.trading(g)
    assert [c for c in server.log if " aoe_trade " in c] == ["scoreboard players set #r12 aoe_trade 1",
                                                             "scoreboard players set #r13 aoe_trade 1"]   # once
    del g.trade["cart"]                                                # the cart died (trade.tick ends the route)
    scenario.trading(g)
    assert server.log[-2:] == ["scoreboard players set #r12 aoe_trade 0", "scoreboard players set #r13 aoe_trade 0"]


def test_read_scenario_keeps_the_building(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Trade")
    t.new_condition.building_is_trading(unit_object=12, inverted=1)
    t.new_effect.send_chat(source_player=1, message="Trade!")
    src = scenarios.save(scn, str(tmp_path / "t.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    c, = trigger["conditions"]
    assert c["type"] == aoe2mc.BUILDING_IS_TRADING and c["ref"] == 12 and c["inverted"]
