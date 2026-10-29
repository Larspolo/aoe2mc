"""The idle town center time of the two players of a recorded game (#4054, check of #4051): Replay.tc_idle equals a
count by hand of the villager trainings of the town centers in samples/de-64.3.aoe2record."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
# By hand from the QUEUE events (each villager 25 s, one after the other); the timeline has no start objects, so a
# town center is alive from its first QUEUE. No research in a town center before 5:00.
# Player 1 (TC 1646, alive 1.976 s): busy to 201.976 s, the next queue at 213.174 s: 11.198 s idle, busy after it.
# Player 2 (TC 1652, alive 0.936 s): gaps 100.936-104.494, 129.494-138.424, 238.424-240.799, 265.799-276.952 s.
HAND = {1: {180000: 0.0, 300000: 11.198}, 2: {180000: 3.558 + 8.930, 300000: 3.558 + 8.930 + 2.375 + 11.153}}


def test_the_idle_town_center_time_of_two_players_equals_the_count_by_hand():
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    assert r.town_centers[0] == {1: {1646: 1976, 12754: 1755299, 16395: 2332980}, 2: {1652: 936, 12470: 1926327}}
    for p, values in HAND.items():
        for t, s in values.items():
            assert abs(r.tc_idle(p, t) - s) < 0.001
    assert r.tc_text(1, 300000) == "0:11" and r.tc_text(2, 300000) == "0:26"


def test_the_summary_names_the_idle_town_center_time_of_each_player_at_the_end():
    r = replay.Replay(Fake(), data(aoe2mc.read_timeline(REC), n=480))
    r.pop, r.ended = {1: 1, 2: 1}, max(e["time"] for e in r.data["timeline"])     # play() sets both
    lines = [c for c in r.summary_commands() if "idle TC time" in c]
    assert [r.tc_text(p) for p in (1, 2)] == ["20:06", "14:22"]               # 3 and 2 town centers up to the end
    for p in (1, 2):
        assert sum(f"idle TC time {r.tc_text(p)}" in c and f"Player {p} " in c for c in lines) == 1
