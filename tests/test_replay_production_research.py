"""The technologies and age-ups in research of each player in the live replay (#2810)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

# Town center 5: 1 villager (25 s), Loom (25 s), Feudal Age (130 s), 1 villager; an unknown technology.
TIMELINE = [{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 1000, "player": 1, "kind": "research", "objects": [5], "technology": "Loom"},
            {"time": 2000, "player": 1, "kind": "research", "objects": [5], "technology": "Feudal Age"},
            {"time": 3000, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
            {"time": 4000, "player": 1, "kind": "research", "objects": [5], "technology": "No Such Tech"}]


def production(t):
    return replay.Replay(Fake(), data(TIMELINE)).production(t)


def test_a_research_waits_for_the_unit_before_it_and_the_units_after_wait_for_it():
    assert production(5000) == {1: [("VILLAGER_MALE", 2, 0, 25000), ("Loom", 25000, 50000, "research"),
                                    ("Feudal Age", 50000, 180000, "age")]}
    assert production(60000) == {1: [("Feudal Age", 50000, 180000, "age"), ("VILLAGER_MALE", 1, 180000, 205000)]}
    assert production(190000) == {1: [("VILLAGER_MALE", 1, 180000, 205000)]}


def test_a_technology_with_no_time_has_no_item_and_one_log_line(capsys):
    r = replay.Replay(Fake(), data(TIMELINE))
    r.production(5000), r.production(6000)
    assert capsys.readouterr().err.count("No Such Tech") == 1
