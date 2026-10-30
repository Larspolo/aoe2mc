"""The view locks of the recording player in aoe2mc.json (#4767): read_timeline thins them to steps of VIEW_TILES."""
import json
import math
import os

import mgz.model
import pytest

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-64.3.aoe2record")


@pytest.fixture(scope="module")
def views():
    state = {}
    aoe2mc.read_timeline(REC, state)
    return state


def test_views_of_the_recorder_are_thinned_and_cover_each_lock(views):
    assert views["recorder"] == 2
    vs = views["views"]
    times = [v["time"] for v in vs]
    assert times == sorted(times)
    assert all(math.dist(a["tile"], b["tile"]) >= aoe2mc.VIEW_TILES for a, b in zip(vs, vs[1:]))
    with open(REC, "rb") as f:
        locks = mgz.model.parse_match(f).file.viewlocks
    k = 0
    for lock in sorted(locks, key=lambda v: v.timestamp):
        t = int(round(lock.timestamp.total_seconds() * 1000))
        while k + 1 < len(vs) and vs[k + 1]["time"] <= t:
            k += 1
        assert math.dist((lock.position.x, lock.position.y), vs[k]["tile"]) < aoe2mc.VIEW_TILES + 1e-3


def test_a_record_without_view_locks_gives_no_views(monkeypatch, tiny_world):
    parse = mgz.model.parse_match

    def no_locks(f):
        m = parse(f)
        m.file.viewlocks = []
        return m
    monkeypatch.setattr(mgz.model, "parse_match", no_locks)
    state = {}
    aoe2mc.read_timeline(REC, state)
    assert "views" not in state and "recorder" not in state
    with open(os.path.join(tiny_world[0], "aoe2mc.json")) as f:
        data = json.load(f)
    assert "views" not in data and "recorder" not in data


def test_views_turn_as_the_timeline_points(views):
    vs = [dict(v, tile=list(v["tile"])) for v in views["views"][:20]]
    size = 120
    aoe2mc.turn_timeline(vs, size, 1)
    for v, w in zip(views["views"], vs):
        assert w["tile"] == [round(float(c), 3) for c in aoe2mc.turn_tile(*v["tile"], size, 1)]
