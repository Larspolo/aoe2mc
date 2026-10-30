"""The live estimate of the wood (#4584): the work technologies of the player make the gather rate of the replay faster."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def test_a_work_technology_makes_the_rate_faster(monkeypatch):
    r = replay.Replay(Fake(), data([]))
    tree = (5, 5)
    r.map = types.SimpleNamespace(fish={}, farms={}, carcasses={}, shore=set(), resource=lambda t: "wood")
    r.gather = gather
    monkeypatch.setattr(gather, "AOE2_WORK", {"wood": 0.5})
    monkeypatch.setattr(gather, "WORK_TECHS", {"AXE": {"wood": 1.2}, "PICK": {"gold": 2}})
    v = types.SimpleNamespace(name="VILLAGER_MALE", tree=tree, player=1)
    assert r.rate(v) == 0.5
    r.learned = {1: [(0, "AXE"), (0, "PICK")], 2: [(0, "AXE")]}
    assert r.rate(v) == pytest.approx(0.6)
    assert replay.Replay.rate(r, types.SimpleNamespace(name="VILLAGER_MALE", tree=tree, player=3)) == 0.5
