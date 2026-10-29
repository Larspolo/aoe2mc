"""Live replay: a trade at a market built in the game shows its text: the record has no name of it (#4322). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_market import trade  # noqa: E402
from test_replay_research import texts  # noqa: E402


def test_a_buy_at_a_market_of_the_game_shows_its_text():
    r = replay.Replay(Fake(), data([]))
    r.commands({"time": 500, "player": 1, "kind": "build", "type": 84, "name": "MARKET", "tile": [8.0, 8.0]})
    (summon,) = texts(r.commands(dict(trade("buy", 100), names=[None])))
    assert "+100 wood" in summon
