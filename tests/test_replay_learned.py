"""Live replay: the researched technologies of each player, with the game time of each one (#3785). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def research(t, tech, player=1):
    return {"time": t, "player": player, "kind": "research", "objects": [5], "names": ["BLACKSMITH"], "technology": tech}


def test_the_researched_technologies_keep_their_game_time():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(60000, "Forging"))
    r.learn(research(120000, "Double-Bit Axe"))
    assert r.learned[1] == [(60000, "FORGING"), (120000, "DOUBLE_BIT_AXE")]
    assert r.upgrades(1, 90000) == ["FORGING"]
    assert r.researched[1] == 2                                      # the count of the summary stays


def test_a_text_with_no_technology_line_keeps_its_text():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(1000, "Some Unknown Tech", player=2))
    assert r.learned[2] == [(1000, "Some Unknown Tech")]
    assert r.upgrades(2, 1000) == ["Some Unknown Tech"] and r.upgrades(1, 1000) == []
