"""Live replay: the Society values of each player in the summary at the end (#1086): castles and wonders built,
tribute sent and received, and the highest villager count. read_timeline keeps the receiver and the resources of an
AoE2 DE tribute."""
import datetime
import json
import os
import sys
import types

import mgz.model

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TIMELINE = [{"time": 1000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE", "amount": 2},
            {"time": 200_000, "player": 1, "kind": "tribute", "to": 2, "food": 0, "wood": 0, "gold": 100, "stone": 0},
            {"time": 1_300_000, "player": 1, "kind": "build", "type": 82, "name": "CASTLE", "tile": [8.0, 8.0]},
            {"time": 1_301_000, "player": 1, "kind": "build", "type": 82, "name": "CASTLE", "tile": [8.0, 8.0]},
            {"time": 1_400_000, "player": 1, "kind": "build", "type": 82, "name": "CASTLE", "tile": [20.0, 8.0]},
            {"time": 1_500_000, "player": 2, "kind": "chat", "text": "gg"}]
WANT = ["Player 1 (Britons): castles 2, wonders 0, relics 0, bought 0, sold 0, tribute sent 100, received 0, villager high 5 (est.)",
        "Player 2 (Aztecs): castles 0, wonders 0, relics 0, bought 0, sold 0, tribute sent 0, received 100, villager high 0 (est.)"]


def lines(sent):
    return ["".join(t["text"] for t in json.loads(c.split(" ", 2)[2])) for c in sent
            if c.startswith("tellraw @a [") and "castles" in c]


def start():
    d = data(TIMELINE)
    d["objects"] = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{i}", "tile": [2.5 + i, 2.5]} for i in range(3)]
    return d


def test_the_summary_shows_the_society_values():
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, start())
    r.run(speed=8, clock=lambda: now[0], sleep=sleep, log=None, bar=True)
    assert lines(game.sent) == WANT


def test_the_census_counts_the_lost_villagers():
    r = replay.Replay(Fake(), start())
    assert r.vhigh == {1: 3}
    r.villager(1, 1)
    r.villager(1, 0, live=1)                                           # two died
    r.villager(1, 1)
    assert r.vills == {1: 2} and r.vhigh == {1: 4}


def test_read_timeline_keeps_the_receiver_and_the_resources_of_a_tribute(tmp_path, monkeypatch):
    action = types.SimpleNamespace(type=types.SimpleNamespace(name="DE_TRIBUTE"), timestamp=datetime.timedelta(seconds=200),
                                   player=types.SimpleNamespace(number=1), position=None,
                                   payload={"target_player_id": b"\x02", "food": 0.0, "wood": 0.0, "gold": 100.0,
                                            "stone": 0.0})
    match = types.SimpleNamespace(actions=[action], chat=[], uptimes=[])
    monkeypatch.setattr(mgz.model, "parse_match", lambda f: match)
    (tmp_path / "r.aoe2record").write_bytes(b"")
    assert aoe2mc.read_timeline(tmp_path / "r.aoe2record") == [
        {"time": 200_000, "player": 1, "kind": "tribute", "to": 2, "food": 0, "wood": 0, "gold": 100, "stone": 0}]
