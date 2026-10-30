"""BACK TO WORK of a unit with no work (#4063): it walks to the last GATHER POINT of its building, as UNGARRISON. In
de-64.3 player 2 set the gather point of its new town center on a tree 4 s before the BACK TO WORK of its builders,
and the replay left them idle for 15 minutes. Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay_garrison import TREE, order, play  # noqa: E402

POINT = dict(time=30000, player=1, kind="gather_point", objects=[50], target=20, tile=[3.5, 12.5],
             names=["TOWN_CENTER"])


def back(t):
    return dict(time=t, player=1, kind="back_to_work", objects=[50], names=["TOWN_CENTER"])


def test_a_unit_with_no_work_goes_to_the_gather_point():
    r, _ = play([order(0, [7], 50, "garrison"), POINT, back(40000)], 80000, extra=[TREE])
    assert r.garrisons == {} and r.units[7].tree == (3, 12) and r.units[7].job == "fletcher"


def test_a_unit_with_no_work_and_no_gather_point_stays_idle():
    r, _ = play([order(0, [7], 50, "garrison"), back(40000)], 80000, extra=[TREE])
    assert r.garrisons == {} and r.units[7].tree is None


def test_a_unit_with_work_goes_back_to_it_not_to_the_gather_point():
    point = dict(POINT, target=None, tile=[14.5, 14.5])
    r, _ = play([order(0, [7], 20), order(20000, [7], 50, "garrison"), point, back(40000)], 80000, extra=[TREE])
    assert r.garrisons == {} and r.units[7].tree == (3, 12) and r.units[7].job == "fletcher"
