"""Live replay: the idle time of the town centers in the summary (#4052). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_army_view import make  # noqa: E402


def queue(t, name="VILLAGER", player=1):
    return {"time": t, "player": player, "kind": "queue", "type": 83, "objects": [5], "name": name}


def test_two_villagers_in_training_leave_50_seconds_idle_in_100():
    r = make([queue(0), queue(60000)])
    assert r.tc_idle(1, 100000) == 50                           # 100 s alive - 2 x 25 s of training


def test_a_technology_in_research_adds_its_seconds_to_the_busy_time():
    loom = {"time": 25000, "player": 1, "kind": "research", "technology": "Loom", "objects": [5]}
    r = make([queue(0), queue(60000), loom])                    # Loom queues behind the villager: 85 s to 110 s
    assert r.tc_idle(1, 100000) == 35                           # 100 - 25 - 25 - the 15 s of Loom up to 100 s
    assert r.tc_idle(1, 200000) == 125                          # 200 - 25 - 25 - the 25 s of Loom


def test_a_player_without_a_town_center_has_no_idle_time():
    r = make([queue(0)])
    assert r.tc_idle(2, 100000) == 0


def test_a_town_center_without_a_start_object_is_alive_from_its_first_villager():
    r = make([queue(60000, player=2)])
    r.data["objects"].clear()                                   # no start object: alive from the QUEUE at 60 s
    assert r.tc_idle(2, 100000) == 15                           # 40 s alive - 25 s of training
    assert r.tc_idle(1, 100000) == 0


def test_the_summary_line_names_the_idle_town_center_time():
    r = make([queue(0), queue(60000)])
    r.villagers = {1: 2}                                        # the summary lists the players with villagers
    r.ended = 100000
    texts = ["".join(t["text"] for t in json.loads(c.split(" ", 2)[2])) for c in r.summary_commands()
             if "villagers trained" in c]
    assert [t for t in texts if t.startswith("Player 1")][0].endswith("idle TC time 0:50")
