"""The water and other airef group types of up-send-scout and up-disband-group-type (#5133). The map of
test_bot_gather: 32 × 32 tiles (tile size 1), the town center of the bot at tile (21, 21)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses


def script(units):
    server, me, b = bot_map()
    me.bots = [b]
    b.g.soldiers.update(units)
    sent = []
    command = b.g.command
    b.g.command = lambda c: sent.append(c) or command(c)
    return per.Script(per.parse(""), b), b, sent


def test_water_explore_sends_one_ship_to_water():
    s, b, sent = script({"g1": "GALLEY", "f1": "FISHING_SHIP", "m1": "MILITIA"})
    m = b.g.map
    m.ground[5][5] = None                                               # one water tile
    s.act(None, ("up-send-scout", "group-type-water-explore", "scout-center"))
    walks = [c for c in sent if c.startswith("aoe moveto")]
    assert walks == [f"aoe moveto f1 5 {m.sea(5, 5)} 5"] and s.sailors == ["f1"]
    s.act(None, ("up-disband-group-type", "group-type-water-explore"))
    assert "aoe stop f1" in sent and s.sailors == []


def test_no_water_or_no_ship_sends_nothing():
    s, b, sent = script({"g1": "GALLEY"})
    s.act(None, ("up-send-scout", "group-type-water-explore", "scout-center"))
    assert not [c for c in sent if c.startswith("aoe moveto")]


def test_disband_the_types_of_the_bot():
    s, b, sent = script({"g1": "GALLEY", "f1": "FISHING_SHIP", "t1": "TRADE_CART", "k1": "MONK"})
    for kind, unit in (("water-attack", "g1"), ("fishing-ship", "f1"), ("land-trade", "t1"), ("monk", "k1")):
        sent.clear()
        assert s.disband(f"group-type-{kind}")
        assert [c for c in sent if c.startswith("aoe stop")] == [f"aoe stop {unit}"]
    s.disband("group-type-transport-ship")
    s.disband("group-type-transport-ship")
    assert s.warned == {("group type", "group-type-transport-ship")}
