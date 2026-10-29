"""Live replay: a jump applies the market trades and the tributes of the skipped time to the estimate and the rates
(#4162). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_market import trade  # noqa: E402

EVENTS = [trade("buy", 100, t=1000), trade("sell", 200, "Food", player=2, t=2000),
          {"time": 3000, "player": 1, "kind": "tribute", "to": 2, "food": 0, "wood": 50, "gold": 0, "stone": 0}]


def test_a_jump_gives_the_estimate_and_rates_of_the_played_events():
    played = replay.Replay(Fake(), data(EVENTS))
    for e in EVENTS:
        played.commands(e)
    jumped = replay.Replay(Fake(), data(EVENTS))
    sent = jumped.jump(EVENTS, 5000)
    assert jumped.stock == played.stock and jumped.rates == played.rates
    assert jumped.rates != replay.Replay(Fake(), data([])).rates
    assert not any("text_display" in c for c in sent)          # no trade texts for the skipped time
