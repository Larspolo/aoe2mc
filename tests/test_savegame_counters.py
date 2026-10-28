"""A saved game keeps the parts of the heal, trickle and repair counters that a tick did not use yet (#2514, epic
#2253): a load gives the same resources and hit points as a game with no save."""
import json

from test_loom import setup

from game import savegame

COUNTERS = {"aura_time": 0.4, "cart_heal": 1.5, "garrison_heal": 0.25, "herd_food": 0.75, "regen_time": 0.5,
            "repair_hp": {(2, 5, 2, 5): 0.3}, "repair_owed": {(2, 5, 2, 5): {"wood": 0.6}}, "whole": {"m"}}


def loaded(g):
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h


def test_a_loaded_game_has_each_counter():
    _, g = setup()
    for k, v in COUNTERS.items():
        setattr(g, k, v)
    h = loaded(g)
    assert {k: vars(h)[k] for k in COUNTERS} == COUNTERS


def test_a_save_before_the_counters_loads():
    _, g = setup()
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    assert not set(savegame.COUNTERS) & set(d["players"]["1"])
    h = loaded(g)
    assert not set(savegame.COUNTERS) & set(vars(h))
