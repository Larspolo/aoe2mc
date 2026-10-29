"""Record Game (#2649): --play --record writes the orders of the game as a timeline, --replay --replay-file plays it."""
import json
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import record  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_spawn import TC  # noqa: E402

MILITIA = {"kind": "unit", "name": "MILITIA", "player": 1, "ref": 7, "uuid": "u-militia", "tile": [10.0, 10.0]}
ENEMY = {"kind": "unit", "name": "ARCHER", "player": 2, "uuid": "u-enemy", "tile": [12.0, 10.0]}   # no ref: a scenario


def world():
    d = data([])
    del d["timeline"]                                                  # a converted scenario has no timeline
    d["objects"] += [TC, MILITIA, ENEMY]
    return d


def game(tmp_path):
    """A short game: a house, a villager of the town center, a move and an attack order."""
    d = world()
    g = types.SimpleNamespace(data=d, player=1, map=types.SimpleNamespace(T=4))
    path = str(tmp_path / "game.jsonl")
    record.start([g], path)
    record.tick(g, 10)
    record.built(g, "HOUSE", (28, 36, 28, 36))                         # footprint x 28..36, z 28..36
    record.queued(g, "VILLAGER_MALE", (8, 24, 8, 24))                  # the town center of aoe2mc.json
    record.tick(g, 25)
    record.trained(g, "u-villager")
    record.ordered(g, "move", {"u-villager", "u-militia"}, cell=(40, 44))
    record.ordered(g, "order", {"u-militia"}, target="u-enemy")
    g.record.f.close()
    return d, path


def test_each_recorded_event_has_the_timeline_keys(tmp_path):
    _, path = game(tmp_path)
    refs, timeline = record.load(path)
    assert refs == {"8,24,8,24": 5, "u-militia": 7, "u-enemy": 8, "28,36,28,36": 9, "u-villager": 10}
    assert [e["kind"] for e in timeline] == ["build", "queue", "move", "order"]
    build, queue, move, order = timeline
    ids = record.types()                                               # the AoE2 type of each name
    assert build == {"time": 10000, "player": 1, "kind": "build", "type": ids["HOUSE"], "name": "HOUSE", "tile": [8.0, 8.0]}
    assert queue == {"time": 10000, "player": 1, "kind": "queue", "type": ids["VILLAGER_MALE"], "name": "VILLAGER_MALE", "objects": [5],
                     "amount": 1}
    assert move == {"time": 35000, "player": 1, "kind": "move", "objects": [7, 10], "tile": [10.125, 11.125]}
    assert order == {"time": 35000, "player": 1, "kind": "order", "objects": [7], "target": 8}
    with open(path) as f:
        assert all(json.loads(line) for line in f)                    # one JSON line per event


def test_a_replay_of_the_file_plays_the_same_events(tmp_path):
    d, path = game(tmp_path)
    d = record.apply(d, path)
    r = replay.Replay(Fake(), d)
    assert [(e["kind"], e["time"]) for e in r.data["timeline"]] == [("build", 10000), ("queue", 10000),
                                                                   ("move", 35000), ("order", 35000)]
    assert next(e for e in r.data["timeline"] if e["kind"] == "move")["names"] == ["MILITIA", "VILLAGER_MALE"]
    assert {o["uuid"]: o["ref"] for o in r.data["objects"] if "uuid" in o} == {"u-militia": 7, "u-enemy": 8}
    spawn, = r.spawns()                                               # the villager of the queue of the town center
    assert spawn["name"] == "VILLAGER_MALE" and spawn["player"] == 1
    cmds = r.commands(r.data["timeline"][0])                          # the house appears
    assert cmds[0].startswith("fill 28 70 28 35 ") and len(cmds) > 2


def test_a_game_with_no_record_writes_nothing():
    g = types.SimpleNamespace(data=world(), player=1, map=types.SimpleNamespace(T=4))
    record.tick(g, 10)
    assert record.event(g, "build") is None
    record.built(g, "HOUSE", (28, 36, 28, 36))
    record.ordered(g, "move", {"u-militia"}, cell=(1, 1))


def test_an_age_is_an_age_event(tmp_path):
    g = types.SimpleNamespace(data=world(), player=2, map=types.SimpleNamespace(T=4))
    record.start([g], str(tmp_path / "age.jsonl"))
    record.aged(g, "LOOM")
    record.aged(g, "FEUDAL_AGE")
    g.record.f.close()
    assert record.load(str(tmp_path / "age.jsonl"))[1] == [{"time": 0, "player": 2, "kind": "age", "age": "FEUDAL_AGE"}]
