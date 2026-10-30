"""Live replay: the idle villager time of each player in the summary (#3757)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_eco import replay_of_map, vill  # noqa: E402


def test_two_idle_villagers_for_30_seconds_give_60_seconds():
    r = replay_of_map()
    vill(r, "VILLAGER_MALE", 1, 1)                              # start villagers: idle (no task yet)
    vill(r, "VILLAGER_MALE", 1, 2)
    r.told = {1: [30_000], 2: [30_000]}                         # the record commands both again (#4063)
    r.idle_time(0)
    r.idle_time(30_000)
    assert r.idled[1] == 60


def test_a_jump_adds_nothing():
    r = replay_of_map()
    vill(r, "VILLAGER_MALE", 1, 1)
    r.told = {1: [330_000]}
    r.idle_time(0)
    r.idle_at = 300_000                                         # the jump in run(): only the new time counts
    r.idle_time(330_000)
    assert r.idled[1] == 30


def test_the_summary_line_ends_with_the_idle_time():
    r = replay_of_map()
    vill(r, "VILLAGER_MALE", 1, 1)
    vill(r, "VILLAGER_MALE", 1, 2)
    r.told = {1: [30_000], 2: [30_000]}
    r.idle_time(0)
    r.idle_time(30_000)
    r.villagers = {1: 2}                                        # the summary lists the players with villagers
    texts = ["".join(t["text"] for t in json.loads(c.split(" ", 2)[2])) for c in r.summary_commands()
             if "villagers trained" in c]
    assert [t for t in texts if t.startswith("Player 1")][0].endswith("idle villager time 1:00, idle TC time 0:00")
