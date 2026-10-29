"""Live replay: the summary of each player counts its market trades (#3941): the amount bought and sold."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake  # noqa: E402
from test_replay_society import lines, start  # noqa: E402

TRADES = [{"time": 100_000, "player": 1, "kind": "buy", "resource": "WOOD", "amount": 100},
          {"time": 110_000, "player": 1, "kind": "buy", "resource": "WOOD", "amount": 100},
          {"time": 120_000, "player": 1, "kind": "sell", "resource": "FOOD", "amount": 500},
          {"time": 130_000, "player": 2, "kind": "chat", "text": "gg"}]


def test_the_summary_counts_the_market_trades():
    d = start()
    d["timeline"] = d["timeline"] + TRADES
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    replay.Replay(game, d).run(speed=8, clock=lambda: now[0], sleep=sleep, log=None, bar=True)
    got = lines(game.sent)
    assert any("Player 1" in x and "bought 200, sold 500" in x for x in got)
    assert any("Player 2" in x and "bought 0, sold 0" in x for x in got)
    assert all(c.count("tellraw") == 1 for c in game.sent if "castles" in c)
