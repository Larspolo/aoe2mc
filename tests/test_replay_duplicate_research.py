"""Live replay: a record with two research events of one technology counts it one time (#3923). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_learned import research  # noqa: E402


def test_a_second_research_of_the_same_technology_counts_one_time():
    r = replay.Replay(Fake(), data([]))
    r.learn(research(2085000, "Iron Casting"))
    r.learn(research(2085000, "Iron Casting"))                     # de-64.3: the same event two times
    r.learn(research(2085000, "Iron Casting", player=2))           # another player: its own research
    assert r.upgrades(1, 2085000) == ["IRON_CASTING"] and r.researched[1] == 1
    assert r.upgrades(2, 2085000) == ["IRON_CASTING"] and r.researched[2] == 1
    assert sum("Iron Casting" in c for c in r.summary_commands()) == 2     # one line of each player
    assert not any(c.count("Iron Casting") > 1 for c in r.summary_commands())
