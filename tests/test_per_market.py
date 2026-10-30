"""game/per.py: an AI script trades at the market, sends tribute and chats to one player (#4573)."""
import diplomacy  # noqa: E402
import market  # noqa: E402
from test_per_rules import run

from game.bot import build  # noqa: F401  (game modules on the path)

SELL = "(defrule (food-amount > 300) (can-sell-commodity food) => (sell-commodity food))"


def with_market(text, steps=1, **stock):
    s, b, server = run("", **stock)
    b.g.sites.append({"name": "MARKET", "footprint": [0, 4, 0, 4], "done": True, "player": b.g.player})
    s.rules = run(text)[0].rules
    for _ in range(steps):
        s.step()
    return s, b, server


def test_sell_food_at_the_price_of_the_market():
    s, b, _ = run("", food=1000, gold=0)
    first = market.price(b.g, "food", False)
    s, b, _ = with_market(SELL, food=1000, gold=0)
    assert b.g.stock["food"] == 900 and b.g.stock["gold"] == first
    second = market.price(b.g, "food", False)
    assert second < first                                              # the price changes after each trade
    s.step()
    assert b.g.stock["food"] == 800 and b.g.stock["gold"] == first + second


def test_no_trade_without_a_market_or_the_resource():
    s, b, _ = run(SELL, food=1000, gold=0)
    assert b.g.stock["food"] == 1000                                   # no market
    s, b, _ = with_market(SELL, food=300, gold=0)
    assert b.g.stock["food"] == 300
    s, b, _ = with_market("(defrule (can-buy-commodity stone) => (buy-commodity stone))", gold=1000, stone=0)
    assert b.g.stock["stone"] == 100 and s.check(("commodity-buying-price", "stone", ">", 0))


def test_tribute_to_player_with_its_fee():
    s, b, _ = with_market("(defrule (true) => (tribute-to-player 1 gold 200) (disable-self))", gold=1000)
    assert b.g.stock["gold"] == 1000 - 2 * diplomacy.cost(b.g, 100)   # the bot of bot_map is player 2
    to = diplomacy.receiver(b.g, 1)
    assert (to.stock["gold"] if to is not None else b.g.tributes[1]["gold"]) == 200


def test_chat_to_player_goes_to_its_team_only():
    s, b, server = run('(defrule (true) => (chat-to-player 2 "Hi") (disable-self))')
    assert any(c.startswith("tellraw @a[team=p2] ") and "Hi" in c for c in server.log)
