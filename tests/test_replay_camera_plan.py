"""Live replay: the camera plan of a record, from its fights and its new buildings (#3366)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))

import aoe2mc  # noqa: E402
import replay  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
OWNER = {100: 1, 200: 2}


def build(t, tile):
    return {"time": t, "player": 1, "kind": "build", "tile": tile}


def attack(t, p, ids, target, tile):
    return {"time": t, "player": p, "kind": "order", "objects": ids, "target": target, "tile": tile}


def test_no_events_make_an_empty_plan():
    assert replay.camera_plan([], OWNER) == []


def test_a_fight_and_a_group_of_buildings_make_shots_and_a_fight_wins():
    fight = [attack(12000, 1, list(range(6)), 200, [30, 30]), attack(17000, 2, list(range(50, 56)), 100, [33, 30])]
    group = [build(12000 + 1000 * i, [50, 50]) for i in range(5)]               # 5 buildings in 4 s
    group_far = [build(0 + 1000 * i, [10, 10]) for i in range(5)]               # 5 buildings at time 0
    plan = replay.camera_plan(sorted(group_far + fight + group, key=lambda e: e["time"]), OWNER)
    assert plan == [{"time": 0, "tile": [10.0, 10.0], "why": "build"},
                    {"time": 12000, "tile": [31.5, 30.0], "why": "fight"}]


def test_a_shot_is_held_for_camera_ms():
    first = [build(1000 * i, [10, 10]) for i in range(5)]                        # a shot at time 0
    second = [build(5000 + 1000 * i, [60, 60]) for i in range(5)]               # 5 s later: no new shot
    assert [(s["time"], s["why"]) for s in replay.camera_plan(first + second, OWNER)] == [(0, "build")]


def test_buildings_spread_over_the_map_make_no_shot():
    spread = [build(1000 * i, [10 * i, 10]) for i in range(5)]                   # 10 tiles apart, one each
    assert replay.camera_plan(spread, OWNER) == []


def test_the_fights_of_the_sample_record_have_a_fight_shot():
    timeline = aoe2mc.read_timeline(REC)
    owner = replay.owners(aoe2mc.read_record(REC)[5], timeline)
    plan = replay.camera_plan(timeline, owner)
    assert plan == sorted(plan, key=lambda s: s["time"])
    for f in replay.fights(timeline, owner):
        assert {"time": f["start"], "tile": f["tile"], "why": "fight"} in plan
