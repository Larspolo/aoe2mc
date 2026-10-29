"""The technologies and age-ups in research of each player in the live replay (#2810)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

V, L, F = aoe2mc.train_ms("VILLAGER_MALE"), replay.RESEARCH_S["Loom"] * 1000, replay.RESEARCH_S["Feudal Age"] * 1000
# Town center 5: 1 villager, Loom, Feudal Age, 1 villager; an unknown technology.
TIMELINE = [{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 1000, "player": 1, "kind": "research", "objects": [5], "technology": "Loom"},
            {"time": 2000, "player": 1, "kind": "research", "objects": [5], "technology": "Feudal Age"},
            {"time": 3000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 4000, "player": 1, "kind": "research", "objects": [5], "technology": "No Such Tech"}]


def production(t):
    return replay.Replay(Fake(), data(TIMELINE)).production(t)


def test_a_research_waits_for_the_unit_before_it_and_the_units_after_wait_for_it():
    up = V + L + F                                                   # the end of the Feudal Age
    assert production(5000) == {1: [("VILLAGER_MALE", 2, 0, V), ("Loom", V, V + L, "research"),
                                    ("Feudal Age", V + L, up, "age")]}
    assert production(V + L + 1) == {1: [("Feudal Age", V + L, up, "age"), ("VILLAGER_MALE", 1, up, up + V)]}
    assert production(up + 1) == {1: [("VILLAGER_MALE", 1, up, up + V)]}


def test_a_technology_with_no_time_has_no_item_and_one_log_line(capsys):
    r = replay.Replay(Fake(), data(TIMELINE))
    r.production(5000), r.production(6000)
    assert capsys.readouterr().err.count("No Such Tech") == 1
