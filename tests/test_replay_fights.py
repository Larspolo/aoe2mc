"""Live replay: the large fights of a record come from its attack orders (#2948)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))

import aoe2mc  # noqa: E402
import replay  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
OWNER = {100: 1, 200: 2, 300: 0}      # a unit of player 1, a unit of player 2, a Gaia object


def attack(t, p, ids, target, tile):
    return {"time": t, "player": p, "kind": "order", "objects": ids, "target": target, "tile": tile}


def battle(t, tile, n=6):
    """Attack orders of both players at game time t (ms) near tile: n units each."""
    return [attack(t, 1, list(range(1000 + t // 1000, 1000 + t // 1000 + n)), 200, tile),
            attack(t + 5000, 2, list(range(5000 + t // 1000, 5000 + t // 1000 + n)), 100, [tile[0] + 3, tile[1]])]


def test_orders_far_apart_in_time_or_place_are_two_fights():
    events = battle(0, [10, 10]) + battle(300000, [12, 10]) + battle(310000, [80, 80])
    out = replay.fights(sorted(events, key=lambda e: e["time"]), OWNER)
    assert [(f["start"], f["players"], f["units"]) for f in out] == [(0, [1, 2], 12), (300000, [1, 2], 12),
                                                                   (310000, [1, 2], 12)]
    assert out[0]["end"] == 5000 and out[0]["tile"] == [11.5, 10.0]


def test_one_side_gaia_targets_and_small_fights_are_no_fights():
    one_side = [attack(0, 1, list(range(20)), 200, [10, 10])]
    gaia = [attack(t, p, list(range(p * 100, p * 100 + 10)), 300, [10, 10]) for t, p in ((0, 1), (1000, 2))]
    own = [attack(t, p, list(range(p * 100, p * 100 + 10)), 100 if p == 1 else 200, [10, 10]) for t, p in ((0, 1), (1000, 2))]
    for events in (one_side, gaia, own, battle(0, [10, 10], n=4)):
        assert replay.fights(events, OWNER) == []


def test_an_attack_move_and_a_chain_of_orders_join_one_fight():
    events = [attack(0, 1, list(range(8)), 200, [10, 10]),
              {"time": 50000, "player": 2, "kind": "attack_move", "objects": list(range(50, 58)), "tile": [20, 10]},
              attack(100000, 1, [1, 2], 200, [30, 10])]        # 100 s after the first order, near the second one
    assert [(f["start"], f["end"], f["units"]) for f in replay.fights(events, OWNER)] == [(0, 100000, 16)]


def test_owners_come_from_the_start_objects_and_the_selections():
    objects = [{"ref": 7, "player": 1, "name": "TOWN_CENTER"}, {"ref": 8, "player": 1, "name": "SHEEP"}]
    events = [{"time": 0, "player": 2, "kind": "move", "objects": [9], "tile": [1, 1]},
              {"time": 0, "player": 2, "kind": "special", "objects": [10]}]
    assert replay.owners(objects, events) == {7: 1, 9: 2}


def test_the_largest_fight_of_the_sample_record():
    objects = aoe2mc.read_record(REC)[5]
    timeline = aoe2mc.read_timeline(REC)
    out = replay.fights(timeline, replay.owners(objects, timeline))
    big = out[0]
    assert big["players"] == [1, 2] and big["units"] >= 30
    assert 35 * 60000 < big["start"] < big["end"] < 41 * 60000          # the late fight of the game
    assert all(0 <= v < 120 for v in big["tile"])                        # on the 120 × 120 map
