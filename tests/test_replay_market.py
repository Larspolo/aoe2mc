"""Live replay: a buy or sell at the market changes the estimated resources and the rate of the player (#3939). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import market  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_learned import research  # noqa: E402


def trade(kind, amount, resource="Wood", player=1, t=1000):
    return {"time": t, "player": player, "kind": kind, "amount": amount, "objects": [12239], "resource": resource}


def test_a_buy_costs_gold_with_the_fee_and_raises_the_rate():
    r = replay.Replay(Fake(), data([]))
    r.commands(trade("buy", 100))
    assert r.stock[1] == {"food": 200, "wood": 300, "gold": 100 - 130, "stone": 200}   # the fee of 30 %: 100 × 1.30
    assert r.rates["wood"] == market.RATES["wood"] + market.STEP


def test_a_sell_of_500_food_is_five_trades_at_the_falling_rate():
    r = replay.Replay(Fake(), data([]))
    r.commands(trade("sell", 500, "Food"))
    rate, gold = market.RATES["food"], 0
    for _ in range(5):
        gold += (rate * (100 - market.FEE) + 50) // 100
        rate -= market.STEP
    assert r.stock[1]["food"] == 200 - 500
    assert r.stock[1]["gold"] == 100 + gold
    assert r.rates["food"] == market.RATES["food"] - 5 * market.STEP


def test_a_player_with_guilds_pays_the_guild_fee():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(500, "GUILDS"))
    r.commands(trade("buy", 100, t=1000))
    assert r.stock[1]["gold"] == 100 - (market.RATES["wood"] * (100 + market.FEES["GUILDS"]) + 50) // 100
