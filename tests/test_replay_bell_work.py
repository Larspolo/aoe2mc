"""BACK TO WORK after a town bell in the live replay (#4063): in de-64.3 villagers of player 2 stood idle to the end
after the bell. A second GARRISON order on the way set their work to None, and the units on the way in at BACK TO WORK
went in later and stayed there. Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay_garrison import TREE, order, play  # noqa: E402


def back(t):
    return dict(time=t, player=1, kind="back_to_work", objects=[50], names=["TOWN_CENTER"])


def test_a_second_bell_keeps_the_work():
    tl = [order(0, [7], 20), order(20000, [7], 50, "garrison"), order(21000, [7], 50, "garrison"), back(40000)]
    r, _ = play(tl, 80000, extra=[TREE])
    assert r.garrisons == {} and r.units[7].tree == (3, 12) and r.units[7].job == "fletcher"


def test_a_unit_on_the_way_in_goes_back_to_work():
    tl = [order(0, [7], 20), order(20000, [7], 50, "garrison"), back(20500)]
    r, _ = play(tl, 80000, extra=[TREE])
    assert r.garrisons == {} and not r.entering and r.units[7].tree == (3, 12) and r.units[7].job == "fletcher"
