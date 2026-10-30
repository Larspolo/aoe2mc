"""A restored replay starts with the ages, technologies and stock of its save (#4592)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

RESTORE = 20 * 60 * 1000
CASTLE = {"food": 500, "wood": 400, "gold": 300, "stone": 100}
FEUDAL = {"food": 50, "wood": 60, "gold": 70, "stone": 80}


def restored(timeline):
    d = data([{"time": RESTORE, "player": None, "kind": "restore"}] + timeline)
    d["players"]["1"].update(saved=True, age="castle", resources=dict(CASTLE), techs=["Loom"])
    d["players"]["2"].update(saved=True, age="feudal", resources=dict(FEUDAL))
    d["objects"] = [{"kind": "unit", "name": "VILLAGER_M", "player": p, "x": 1, "y": 1,
                     "uuid": [p, 0, 0, 0]} for p in (1, 2)]
    return d


def test_panel_starts_with_the_state_of_the_save():
    game = Clock()
    r = replay.Replay(game, restored([{"time": RESTORE + 5000, "player": 1, "kind": "chat", "text": "t1"}]))
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, bar=True)
    assert (r.ages[1], r.ages[2]) == ("Castle", "Feudal")
    assert r.resources(1) == CASTLE and r.resources(2) == FEUDAL
    assert r.upgrades(1, RESTORE) == ["LOOM"] and r.upgrades(2, RESTORE) == []
    assert set(r.reached[1]) == {"FEUDAL_AGE", "CASTLE_AGE"}
    assert "Castle · F 500 W 400 G 300 S 100" in r.named[1]


def test_an_age_or_technology_of_the_save_is_not_paid_again():
    r = replay.Replay(Clock(), restored([]))
    r.age({"time": RESTORE + 1000, "player": 1, "kind": "age", "age": "CASTLE_AGE"})
    r.learn({"time": RESTORE + 1000, "player": 1, "kind": "research", "technology": "Loom"})
    assert r.resources(1) == CASTLE and r.researched[1] == 1


def test_a_record_that_is_not_restored_starts_as_before():
    d = restored([])
    d["timeline"] = []
    r = replay.Replay(Clock(), d)
    assert r.ages == {} and r.reached == {} and r.resources(1) == replay.START
