"""The units in training of each player in the live replay (#2809): the state of the production panel (#2807)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

V, M, L = aoe2mc.train_ms("VILLAGER_MALE"), aoe2mc.train_ms("MILITIA"), replay.RESEARCH_S["Loom"] * 1000   # ms of the data
# Town center 5 of player 1: 1 villager, Loom, 2 villagers; barracks 9 of player 2: 1 militia.
TIMELINE = [{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 0, "player": 2, "kind": "queue", "type": 74, "objects": [9], "name": "MILITIA"},
            {"time": 1000, "player": 1, "kind": "research", "objects": [5], "technology": "Loom"},
            {"time": 2000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE",
             "amount": 2}]


def production(t):
    return replay.Replay(Fake(), data(TIMELINE)).production(t)


def test_a_queue_counts_from_its_command_and_shows_the_first_unit():
    assert production(1500) == {1: [("VILLAGER_MALE", 1, 0, V), ("Loom", V, V + L, "research")], 2: [("MILITIA", 1, 0, M)]}
    assert production(10000) == {1: [("VILLAGER_MALE", 3, 0, V), ("Loom", V, V + L, "research")], 2: [("MILITIA", 1, 0, M)]}


def test_a_unit_leaves_at_its_end_and_a_research_delays_the_next_ones():
    assert production(V)[1] == [("Loom", V, V + L, "research"), ("VILLAGER_MALE", 2, V + L, 2 * V + L)]
    assert production(2 * V + L + 5000)[1] == [("VILLAGER_MALE", 1, 2 * V + L, 3 * V + L)]
    assert production(max(3 * V + L, M)) == {}


def test_two_buildings_of_one_player_group_by_name_in_the_order_of_the_next_end():
    timeline = [{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
                {"time": 0, "player": 1, "kind": "queue", "type": 74, "objects": [9], "name": "MILITIA", "amount": 2},
                {"time": 5000, "player": 1, "kind": "queue", "type": 83, "objects": [6], "name": "VILLAGER_MALE"}]
    assert replay.Replay(Fake(), data(timeline)).production(6000) == {
        1: sorted([("MILITIA", 2, 0, M), ("VILLAGER_MALE", 2, 0, V)], key=lambda item: item[3])}
