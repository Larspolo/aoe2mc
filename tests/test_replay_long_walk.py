"""A new order of a walking unit on Paper starts its path at a free cell (#2881): the replay position on the straight line
of the old leg can be in a lake or a forest, the path search from there found no path, and the unit got one straight
leg to its goal (eagle scout 15315 of de-63.0: 490 blocks, 180 blocks behind its replay position for 2 minutes)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

UNIT = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [2.5, 2.5]}


def lake(*more):
    """A replay on Paper of a map of 64 × 64 blocks with a lake at x 20 to 40, z 0 to 48: a walk from the east shore
    to the west shore goes around its south end."""
    d = data([])
    d["ground"] = [" ".join("-" if 20 <= x <= 40 and z < 48 else "70" for x in range(64)) for z in range(64)]
    d["objects"] = [UNIT, *more]
    r = replay.Replay(Fake(), d, ai=True)
    r.grid()                                                                # the start units
    return r


def test_a_new_order_in_the_middle_of_a_leg_over_a_lake_walks_around_it():
    r = lake()
    v = r.unit(7, "VILLAGER_MALE", 1)
    v.pos, v.leg = (54.5, 70.0, 10.5), ((10.5, 70.0, 10.5), 0, 20000)      # at 10 s the leg is over the lake
    assert not r.map.free(*map(int, r.at(v, 10000)[::2]))
    cmds = r.move(dict(time=10000, player=1, kind="move", objects=[7], tile=[1.5, 2.5], names=["VILLAGER_MALE"]))
    start = v.leg[0]
    assert r.map.free(int(start[0]), int(start[2]))                         # the near (east) shore, not the water
    assert start[0] > 40
    walk = [c for c in cmds if c.startswith("aoe moveto")]
    assert walk and walk[0] != "aoe moveto u1 6.5 70.0 10.5"                  # a leg on the land, not over the lake
    assert 7 in r.moving and v.path and all(r.map.free(*c) for c in v.path)


def test_a_unit_that_stands_keeps_its_place():
    r = lake()
    v = r.unit(7, "VILLAGER_MALE", 1)
    assert r.stop_at(v, 5000) == v.pos
    v.pos, v.leg = (54.5, 70.0, 10.5), ((10.5, 70.0, 10.5), 0, 20000)
    assert r.stop_at(v, 4000) == r.at(v, 4000)                              # on the land before the lake


def test_a_follower_with_no_path_searches_again_at_the_end_of_its_leg(monkeypatch):
    """A follower with no path walks one straight leg and is not in `moving`: chase() gave it a new move with a new
    search (0.2 s at the limit) at each step while its target walked, 153 searches in one game minute of de-63.0."""
    r = lake(dict(UNIT, uuid="u2", ref=8, tile=[14.5, 14.5]))
    searches = []
    monkeypatch.setattr(r.map, "path", lambda *a, **k: searches.append(a) and None)
    r.escort(dict(time=0, player=1, kind="follow", objects=[7], target=8, names=["VILLAGER_MALE"]))
    first, v, w = len(searches), r.units[7], r.units[8]
    assert first and v.leg[2] > 15000
    for t in range(1000, 15000, 1000):                                     # the target walks on
        w.pos = (58.5 + t / 2000, 70.0, 58.5)
        r.chase(t)
    assert len(searches) == first
    w.pos = (40.5, 70.0, 58.5)
    r.chase(int(v.leg[2]) + 1000)                                          # its leg ends: it searches again
    assert len(searches) > first


def test_a_far_goal_gets_a_search_that_grows_with_its_distance(monkeypatch):
    """A way around a forest of de-63.0 (270 blocks) needed more than PATH_CELLS cells: the unit got one straight leg."""
    monkeypatch.setattr(replay, "PATH_CELLS", 1000)
    r = lake()
    v = r.units[7]
    v.pos = (45.5, 70.0, 10.5)                                              # the east shore
    assert r.map.path(v.cell, {(6, 10)}, replay.PATH_CELLS) is None          # the old limit: no path
    r.move(dict(time=0, player=1, kind="move", objects=[7], tile=[1.5, 2.5], names=["VILLAGER_MALE"]))
    assert 7 in r.moving and v.path and v.path[-1] == (6, 10)
