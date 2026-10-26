"""Live replay on Paper: a new order starts where the unit is on its leg, not at the end of the leg (#851). Fake RCON."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay_ai import orders, play  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

EAST = dict(time=0, player=1, kind="move", objects=[7], tile=[12.5, 10.5])     # 40 blocks east of (10, 42)


def test_the_replay_position_moves_on_the_leg():
    r, _, _ = play([EAST], (VIL,))
    v = r.units[7]
    speed = replay.SPEEDS["VILLAGER"] * r.T                                       # blocks per game second
    assert v.pos[::2] == (50.5, 42.5) and v.leg[0][::2] == (10.0, 42.0) and v.leg[1] == 0
    assert math.isclose(v.leg[2], 1000 * math.dist((10, 42), (50.5, 42.5)) / speed)
    x, y, z = r.at(v, v.leg[2] / 2)
    assert math.isclose(x, 30.25) and math.isclose(z, 42.25) and y == v.pos[1]    # half of the way
    assert r.at(v, v.leg[2]) == v.pos                                          # at the end of the leg
    assert r.at(gather.Villager("u9", (1.5, 70.0, 2.5)), 5000) == (1.5, 70.0, 2.5)    # no leg


def test_a_new_order_starts_where_the_unit_is():
    """A scout gets a new order every few seconds: its new leg starts on the old leg, so the replay position
    does not jump ahead of the unit."""
    north = dict(time=5000, player=1, kind="move", objects=[7], tile=[6.5, 2.5])          # to (26.5, 10.5)
    r, sent, _ = play([EAST, north], (VIL,))
    v, speed = r.units[7], replay.SPEEDS["VILLAGER"] * r.T
    (x0, _, z0), t0, t1 = v.leg
    assert t0 == 5000 and math.isclose(x0, 10 + 5 * speed, rel_tol=1e-3) and 42 < z0 < 42.5    # not at x 50.5
    assert math.isclose(t1 - t0, 1000 * math.dist((x0, z0), v.pos[::2]) / speed)
    assert orders(sent)["u1"][::2] == v.pos[::2] == (26.5, 10.5)
