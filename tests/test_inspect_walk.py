"""Live replay: a spectator sees the info line of a walking unit at its place on the leg, Replay.at() (#5312)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_inspect import bars, setup  # noqa: E402


def walking():
    """The unit walks from x 10 to x 30 (z 30) from 10 s to 20 s game time: at 15 s it is at x 20."""
    r = setup()
    v = r.units[7]
    v.pos = (30.0, 70.0, 30.0)
    v.leg = ((10.0, 70.0, 30.0), 10000, 20000)
    return r


def look_from(r, x):
    r.eye = lambda name: ((x, 71.62, 40.0), (0.0, 0.0, -1.0))   # north, at z 30


def test_a_ray_through_the_place_on_the_leg_gives_the_line():
    r = walking()
    look_from(r, 20.0)
    assert bars(r.inspect(15000, clock=lambda: 0.0))


def test_a_ray_through_the_end_of_the_leg_gives_no_unit_line():
    r = walking()
    look_from(r, 30.0)
    assert not bars(r.inspect(15000, clock=lambda: 0.0))
