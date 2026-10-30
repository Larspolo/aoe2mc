"""Live replay: the build order of the sample record up to 10:00 matches the commands of the record (#4050)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

import aoe2mc  # noqa: E402
import units  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
END = 600000


@pytest.fixture(scope="module")
def events():
    pytest.importorskip("mgz")
    return aoe2mc.read_timeline(REC)


def test_the_build_order_of_the_record_holds_the_first_building_of_each_type_in_time_order(events):
    r = replay.Replay(Fake(), data(events))
    for p in (1, 2):
        steps = r.build_order(p, END)
        first = {}
        for e in sorted(events, key=lambda e: e["time"]):
            if e.get("player") == p and e["kind"] == "build" and e["time"] <= END:
                first.setdefault(e["name"], e["time"])
        assert steps and [t for t, _ in steps] == sorted(t for t, _ in steps)
        assert all(t <= END for t, _ in steps)
        got = {label: t for t, label in steps}
        for name, t in first.items():
            assert got[units.pretty(name)] == t
        assert all(not label.isupper() for _, label in steps)   # readable names, not "BARRACKS" (#4145)
