"""Replay.grid works on each call: the buildings of later events go into the map too, also a farm (#788)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402


def test_a_farm_after_the_first_grid():
    r = replay.Replay(Fake(), data([]))
    assert r.commands(build(tile=(4.0, 4.0), t=1000)) and r.grid()
    farm = dict(build(tile=(10.5, 10.5), t=2000), type=50, name="FARM")
    assert r.commands(farm)                                            # no error at the second building
    m = r.grid()
    (_, house, (x0, x1, z0, z1)), (_, name, (f0, f1, g0, g1)) = r.placed
    assert all((x, z) in m.blocked for x in range(x0, x1) for z in range(z0, z1))
    assert name == "FARM" and m.farm_at[(f0, g0)] == ((f0 + f1) // 2 // 4, (g0 + g1) // 2 // 4)   # the farm key (#719)
