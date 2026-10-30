"""Live replay: a buy or sell at the market changes the estimated resources and the rate of the player (#3939). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import market  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_learned import research  # noqa: E402


def trade(kind, amount, resource="Wood", player=1, t=1000):
    return {"time": t, "player": player, "kind": kind, "amount": amount, "objects": [12239], "resource": resource}


def test_a_buy_costs_gold_with_the_fee_and_raises_the_rate():
    r = replay.Replay(Fake(), data([]))
    r.commands(trade("buy", 100))
    cost = (market.RATES["wood"] * (100 + market.FEE) + 50) // 100   # the gold of 100 wood with the fee
    S = replay.START
    assert r.stock[1] == dict(S, wood=S["wood"] + 100, gold=S["gold"] - cost)
    assert r.rates["wood"] == market.RATES["wood"] + market.STEP


def test_a_sell_of_500_food_is_five_trades_at_the_falling_rate():
    r = replay.Replay(Fake(), data([]))
    r.commands(trade("sell", 500, "Food"))
    rate, gold = market.RATES["food"], 0
    for _ in range(5):
        gold += (rate * (100 - market.FEE) + 50) // 100
        rate -= market.STEP
    assert r.stock[1]["food"] == replay.START["food"] - 500
    assert r.stock[1]["gold"] == replay.START["gold"] + gold
    assert r.rates["food"] == market.RATES["food"] - 5 * market.STEP


def test_a_player_with_guilds_pays_the_guild_fee():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(500, "GUILDS"))
    r.commands(trade("buy", 100, t=1000))
    guilds = train.COSTS["GUILDS"].get("gold", 0)                     # the research pays its cost (#4389)
    assert r.stock[1]["gold"] == replay.START["gold"] - guilds - (market.RATES["wood"] * (100 + market.FEES["GUILDS"]) + 50) // 100
