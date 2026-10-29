"""The statistics of each player at each game minute of the live replay (#3446): the base of the graphs."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

UNITS = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [2.5, 8.5]},
         {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 2, "uuid": "u2", "ref": 8, "tile": [4.5, 8.5]}]


def game():
    d = data([])
    d["objects"] = UNITS
    return replay.Replay(Fake(), d)


def test_one_sample_per_minute_with_the_values_of_that_time():
    r = game()
    r.sample(0)
    r.villager(1, 2)
    r.pop[1] += 2
    r.gathered[1] = {"food": 120.4, "wood": 30, "gold": 0, "stone": 0}
    r.sample(30000)                                     # the same minute: no new sample
    r.sample(61000)
    assert r.stats(61000) == {1: [(0, 1, 1, 0, 0), (1, 3, 3, 0, 150)], 2: [(0, 1, 0, 1, 0), (1, 1, 0, 1, 0)]}
    assert r.stats(59999) == {1: [(0, 1, 1, 0, 0)], 2: [(0, 1, 0, 1, 0)]}


def test_a_jump_keeps_one_sample_per_minute():
    r = game()
    r.sample(0)
    r.pop[2] += 4
    r.sample(185000)                                    # a jump from 0:00 to 3:05
    assert [s[0] for s in r.stats(185000)[2]] == [0, 1, 2, 3]
    assert r.stats(185000)[2][1:] == [(m, 5, 0, 5, 0) for m in (1, 2, 3)]
