"""Live replay on Paper: a builder whose replay unit is next to the foundation already (no path) gets an order to its
cell, and settle() checks that its entity gets there (#2634). In de-64.3 such a builder got no order: its entity walked
on to the goal of its last walk and stood there, 30 blocks from its replay position. Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_catch_up import Entity  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def builder(game):
    d = data([dict(time=1000, player=1, kind="chat", text="go")], n=128)
    d["objects"] += [VIL]
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: 0.0, sleep=lambda s: None, log=None, finish=True)
    return r, r.units[7]


def test_a_builder_with_no_path_walks_to_its_cell():
    r, v = builder(Entity(at=(40.5, 42.5)))                        # the entity is on its way to an old goal
    out = r.go(7, v, None, [], 2000)
    end = "{} {} {}".format(*v.pos)
    assert f"aoe moveto u1 {end}" in out and v.cell == (10, 42) and 7 in r.idle
    assert f"aoe moveto u1 {end}" in r.steps(r.idle[7][0])  # it stands far from its cell: settle()


def test_a_builder_at_its_cell_gets_no_second_order():
    r, v = builder(Entity(at=(10.5, 42.5)))
    r.go(7, v, None, [], 2000)
    assert not [c for c in r.steps(r.idle[7][0]) if c.startswith(("aoe moveto", "tp "))] and 7 not in r.idle
