"""Live replay: the overview at the start shows the ground, not only clouds (#1094). On the 480 x 480 record map the view
was 205 blocks from the ground (more than the render distance 12) and above the clouds."""
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def view(r):
    tp = next(c for c in r.overview() if c.startswith("tp @a "))
    return tuple(map(float, re.match(r"tp @a (\S+) (\S+) (\S+) facing (\S+) (\S+) (\S+)$", tp).groups()))


def test_the_view_of_a_large_map_is_near_the_ground_and_below_the_clouds():
    d = data([], n=480, y=64)
    d["ground"][0] = " ".join(["85"] * 480)                               # a hill at the edge: not the center height
    x, y, z, fx, fy, fz = view(replay.Replay(Fake(), d))
    assert (fx, fy, fz) == (240, 64, 240)                                 # the ground at the center
    assert y < replay.CLOUDS
    assert math.dist((x, y, z), (fx, fy, fz)) <= replay.VIEW_DIST <= 12 * 16
    assert abs(math.degrees(math.atan2(y - fy, math.hypot(x - fx, z - fz))) - replay.VIEW_PITCH) < 1


def test_the_view_of_a_small_map_stays_low():
    x, y, z, *_ = view(replay.Replay(Fake(), data([], n=64, y=70)))
    assert y == 70 + 64 // 3


def test_the_view_stays_above_high_ground():
    x, y, z, fx, fy, fz = view(replay.Replay(Fake(), data([], n=480, y=200)))
    assert fy == 200 and y > 200
