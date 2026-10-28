"""Live replay on Paper: a unit that ends its walk far from its replay position, with no new order, walks there
again and at last goes there with /tp (Replay.settle, #2633). Fake RCON."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_catch_up import Entity  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def run(game, tl):
    d = data(tl, n=128)
    d["objects"] += [VIL]
    now = [0.0]
    replay.Replay(game, d, ai=True).run(4.0, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s),
                                        log=None, finish=True)
    return [c for c in game.sent if re.match(r"(aoe moveto|tp) u1 ", c)]


def test_a_unit_far_from_the_end_of_its_walk_walks_there_again_then_gets_a_tp():
    walk = [dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5])]
    orders = run(Entity(at=(10.5, 42.5)), walk)                    # the entity stays at the start of the walk
    first, *again, tp = orders
    end = first.split(" ", 3)[3]
    assert again and set(again) == {f"aoe moveto u1 {end}"}        # from its own place, to the end of the walk
    assert tp == f"tp u1 {end}" and len(again) <= replay.HOME_MS // replay.STILL


def test_a_unit_at_the_end_of_its_walk_gets_no_new_order():
    walk = [dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5])]
    assert len(run(Entity(), walk)) == 1                           # at the end of its leg: it got there


def test_a_new_order_ends_the_checks():
    walk = [dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5]),
            dict(time=14000, player=1, kind="move", objects=[7], tile=[2.5, 10.5])]   # back to the entity
    orders = run(Entity(at=(10.5, 42.5)), walk)
    assert len(orders) == 2 and not [c for c in orders if c.startswith("tp ")]


def test_a_unit_behind_its_leg_walks_to_the_place_of_its_stop():
    walk = [dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5]),
            dict(time=8000, player=1, kind="stop", objects=[7])]
    orders = run(Entity(at=(10.5, 42.5)), walk)
    x = float(orders[1].split()[3])
    assert 10.5 + replay.HOME < x < 50.5 and orders[1].startswith("aoe moveto u1 ")   # on the leg, not its end
    assert orders[-1] == "tp u1 " + orders[1].split(" ", 3)[3]
