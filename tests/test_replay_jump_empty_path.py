"""A unit in `moving` with an empty path stops in steps() with no exception (#1177: a long jump of the live replay
without the plugin stopped with an IndexError)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402


@pytest.mark.parametrize("ship", [False, True])
def test_a_unit_with_an_empty_path_stops(ship):
    r = replay.Replay(Clock(), data([]))
    r.grid()
    r.units[7] = v = r.gather.Villager("u1", (2.5, 70.0, 2.5))
    v.name = "GALLEY" if ship else "VILLAGER_MALE"
    r.moving[7] = 1000.0
    r.steps(2000.0)
    assert 7 not in r.moving and v.pos == (2.5, 70.0, 2.5)


def test_a_unit_that_goes_inside_stops_its_walk():
    from test_replay_garrison import RECT, TC
    d = data([])
    d["objects"] += [TC]
    r = replay.Replay(Clock(), d)
    r.grid()
    r.units[7] = v = r.gather.Villager("u1", (20.5, 70.0, 20.5))
    v.name, v.path = "VILLAGER_MALE", [(21, 20), (22, 20)]
    r.moving[7], r.entering[7] = 5000.0, [RECT, TC, 1000.0]
    r.enter(2000.0)
    assert r.garrisons == {RECT: [7]} and not v.path and 7 not in r.moving
