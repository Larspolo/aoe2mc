"""game/bot.py: an allied bot sends its extra resources by taunts 38, 58 and 60 and stops by taunt 59 (#4830), on the
map of test_bot_gather (the bot is player 2, the person is player 1)."""
import diplomacy  # noqa: E402
import market  # noqa: E402
from test_bot_gather import bot_map

from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)


def setup(monkeypatch, has_market=True):
    server, me, b = bot_map()
    for p in ("1", "2"):
        b.g.players.setdefault(p, {})["team"] = 1
    monkeypatch.setattr(market, "markets", lambda g: [(0, 1, 0, 1)] if has_market and g is b.g else [])
    monkeypatch.setattr(b, "reserve", lambda: {"wood": 100})
    b.g.stock.update(food=0, wood=900, gold=0, stone=0)
    return server, me, b


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]   # as gather.Game.clicks keeps them (#4827)


def test_taunt_38_sends_the_extra_wood_and_59_stops(monkeypatch):
    server, me, b = setup(monkeypatch)
    wood = me.stock["wood"]
    b.give()
    assert b.g.stock["wood"] == 900                       # no ask yet
    taunt(me, 38)
    b.give()
    assert b.g.stock["wood"] - 100 < diplomacy.cost(b.g, diplomacy.LOT) and me.stock["wood"] > wood
    assert b.g.stock["wood"] >= 100                       # the reserve stays
    taunt(me, 59)
    b.g.stock["wood"] = 900
    b.give()
    assert b.g.stock["wood"] == 900


def test_no_market_sends_nothing_and_says_so_once(monkeypatch):
    server, me, b = setup(monkeypatch, has_market=False)
    sent = []
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: sent.append(c) or command(c))
    taunt(me, 38)
    b.give()
    b.give()
    assert b.g.stock["wood"] == 900
    assert sum("aoe2mc.bot.no_market" in c for c in sent) == 1
