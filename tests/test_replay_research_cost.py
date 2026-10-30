"""Live replay: a research of the record pays its cost in the resource estimate (#4389)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
import train  # noqa: E402
from test_replay import Fake, data  # noqa: E402

S = replay.START


def make():
    return replay.Replay(Fake(), data([]))


def research(r, tech, t=100_000):
    r.commands({"time": t, "player": 1, "kind": "research", "technology": tech})


def test_a_research_pays_its_cost_once():
    r = make()
    research(r, "Loom")
    after = {k: S[k] - train.COSTS["LOOM"].get(k, 0) for k in S}
    assert r.resources(1) == after and after != S
    research(r, "Loom", 200_000)                                     # a second event of the same technology
    assert r.resources(1) == after
    assert r.resources(2) == S


def test_an_age_research_pays_nothing():
    r = make()
    research(r, "Feudal Age")
    assert r.resources(1) == S
