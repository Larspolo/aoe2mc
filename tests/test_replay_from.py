"""The live replay with --from starts with the state of that game time (#3025): the buildings and the units of the
skipped time are there, not only the events from that time on."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import build, data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

import replay  # noqa: E402


def world():
    timeline = [build(name="HOUSE", t=5000, tile=(8.0, 8.0)),
                {"time": 1000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
                {"time": 40000, "player": 1, "kind": "chat", "text": "t40000"}]
    d = data(timeline)
    d["objects"] += [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [4.0, 4.0],
                      "footprint": [8, 24, 8, 24]}]
    return d


def test_a_live_replay_from_a_later_time_has_the_buildings_and_the_units_before_it():
    game = Clock()
    made = []

    def make():
        made.append(replay.Replay(game, world()))
        return made[-1]
    replay.live(make, 4.0, 10000, clock=lambda: game.now, sleep=game.sleep, log=None)
    r = made[0]
    assert [p[1] for p in r.placed] == ["HOUSE"] and any(c.startswith("fill") for c in game.sent)   # 5 s, before 10 s
    assert r.villagers == {1: 1}                                # the VILLAGER_MALE of the queue at 1 s (spawn 26 s)
