"""Live replay: the idle town center time in the score panel (#4053). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_army_view import make  # noqa: E402


def queue(t, name="VILLAGER", player=1):
    return {"time": t, "player": player, "kind": "queue", "type": 83, "objects": [5], "name": name}


def names(cmds):
    return [json.loads(c.split(" ", 6)[6])["text"] for c in cmds if " display name P1 " in c]


def test_the_display_name_shows_the_idle_town_center_time_of_the_case():
    r = make([queue(0), queue(60000)])                          # 100 s alive - 2 x 25 s of training: 50 s idle
    r.pop, r.ages = {1: 1}, {1: "Dark"}
    assert names(r.score_commands(100_000))[0].endswith("· APM 1 · TC idle 0:50")


def test_a_second_call_at_the_same_time_sends_no_name():
    r = make([queue(0), queue(60000)])
    r.pop, r.ages = {1: 1}, {1: "Dark"}
    r.score_commands(100_000)
    assert names(r.score_commands(100_000)) == []
