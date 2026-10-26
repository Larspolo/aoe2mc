"""Live replay: the overview of a map with a lake at the center looks at the water, not at the highest ground (#1150).
On `samples/de-64.3.aoe2record` the center height was the hill top (104), so the camera stood 126 blocks above the lake
and the fog of the client hid the ground."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_overview_height import view  # noqa: E402


def lake(n=480, y=64, hill=104, r=40):
    """A map at height y with a hill on one edge and a round lake ("-": water) of radius r blocks at the center."""
    d = data([], n=n, y=y)
    rows = [row.split() for row in d["ground"]]
    rows[0] = [str(hill)] * n
    for z in range(n):
        for x in range(n):
            if math.hypot(x - n / 2, z - n / 2) < r:
                rows[z][x] = "-"
    d["ground"] = [" ".join(row) for row in rows]
    return d


def test_the_view_of_a_lake_looks_at_the_water():
    x, y, z, fx, fy, fz = view(replay.Replay(Fake(), lake()))
    assert (fx, fy, fz) == (240, 64, 240)                               # the lowest ground, not the hill (104)
    assert math.dist((x, y, z), (fx, fy, fz)) <= replay.VIEW_DIST


def test_the_lake_height_is_the_lowest_ground():
    x, y, z, fx, fy, fz = view(replay.Replay(Fake(), lake(y=70, hill=90)))
    assert fy == 70 and y - fy <= replay.VIEW_DIST * math.sin(math.radians(replay.VIEW_PITCH)) + 1
