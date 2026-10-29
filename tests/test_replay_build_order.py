"""Live replay: the build order of each player up to a game time (#4047). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [8.0, 8.0], "footprint": [26, 26, 38, 38]}


def make(timeline=()):
    d = data(list(timeline))
    d["objects"].append(TC)
    return replay.Replay(Fake(), d)


def timeline():
    return [
        {"time": 30000, "player": 1, "kind": "build", "type": 70, "name": "HOUSE", "tile": [8.0, 8.0]},
        {"time": 40000, "player": 1, "kind": "build", "type": 70, "name": "HOUSE", "tile": [9.0, 8.0]},
        {"time": 5000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER"},
        {"time": 90000, "player": 1, "kind": "queue", "type": 4, "objects": [5], "name": "ARCHER"},
        {"time": 20000, "player": 1, "kind": "research", "technology": "Loom"},
        {"time": 50000, "player": 1, "kind": "research", "technology": "Feudal Age"},
        {"time": 180000, "player": 1, "kind": "age", "age": "FEUDAL_AGE"},
    ]


def test_the_build_order_gives_the_first_of_each_type_in_time_order_up_to_the_time():
    r = make(timeline())
    assert r.build_order(1, 100000) == [(20000, "Loom"), (30000, "House"), (90000, "Archer")]


def test_the_age_and_the_later_steps_show_at_a_later_time():
    r = make(timeline())
    assert r.build_order(1, 200000)[-1] == (180000, "Feudal Age")
    assert r.build_order(1, 200000)[-2:] == [(90000, "Archer"), (180000, "Feudal Age")]


def test_a_player_without_events_has_no_build_order():
    r = make(timeline())
    assert r.build_order(2, 100000) == []
