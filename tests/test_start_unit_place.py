"""The start units of a converted record stand at their start tile (#2667)."""
import contextlib
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import replay_drift  # noqa: E402


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    pytest.importorskip("mgz")
    import aoe2mc
    w = str(tmp_path_factory.mktemp("start") / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(os.path.join(ROOT, "samples", "de-64.3.aoe2record"), w)
    with open(os.path.join(w, "aoe2mc.json")) as f:
        return w, json.load(f)


def test_each_start_unit_stands_at_its_tile(world):
    w, data = world
    assert any(o.get("ref") == 1665 for o in data["objects"])      # the eagle scout of #2667
    assert replay_drift.played(w, data) == []


def test_a_unit_off_its_tile_is_found(world):
    w, data = world
    moved = json.loads(json.dumps(data))
    o = next(o for o in moved["objects"] if o.get("ref") == 1665)
    o["tile"] = [20.5, 79.0]                                        # its place at 11:55 in the record
    assert replay_drift.played(w, moved) == [1665]
