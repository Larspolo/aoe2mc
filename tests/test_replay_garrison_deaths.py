"""Live replay: a villager that dies inside a building leaves the garrison (#4063). On Paper the live replay of de-64.3
stopped at 31:00 with a KeyError: bury() took the dead villager out of the units, and BACK TO WORK let it out."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_eco import replay_of_map, vill  # noqa: E402
from test_replay_fight_deaths import Server  # noqa: E402

RECT = (16, 32, 16, 32)


def garrisoned():
    r = replay_of_map()
    r.game = Server({"u1", "u2"})
    r.starts = [(5, 1, "TOWN_CENTER", RECT)]
    for k in (1, 2):
        vill(r, "VILLAGER_MALE", 1, k)
    r.garrisons[RECT] = [1, 2]
    r.work.update({1: (2, 2), 2: (3, 3)})
    r.pop, r.troops = {1: 2}, {}
    r.census()
    r.game.live.discard("u2")                                   # died inside: no timeline event
    r.census()
    return r


def test_a_dead_villager_leaves_the_garrison():
    r = garrisoned()
    assert r.garrisons[RECT] == [1] and 2 not in r.work


def test_back_to_work_lets_out_only_the_live_villagers():
    r = garrisoned()
    r.commands({"time": 60_000, "player": 1, "kind": "back_to_work", "objects": [5], "names": ["TOWN_CENTER"]})
    assert RECT not in r.garrisons and r.units[1].tree == (2, 2)
