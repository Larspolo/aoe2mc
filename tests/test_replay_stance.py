"""Live replay on Paper: the STANCE action of the record sets the AoE2 stance of the military units (#2548). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL, play  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402


def stances(sent):
    return [c for c in sent if c.startswith("aoe stance ")]


def test_a_stance_sets_the_military_units_and_not_the_villagers():
    e = dict(time=0, player=1, kind="stance", objects=[7, 8], stance="Stand Ground")
    _, sent, _ = play([e], (VIL, MIL, HOUSE))
    assert stances(sent) == ["aoe stance u2 stand_ground"]
    for name, stance in (("Aggressive", "aggressive"), ("Defensive", "defensive"), ("No Attack", "no_attack")):
        _, sent, _ = play([dict(e, stance=name)], (VIL, MIL, HOUSE))
        assert stances(sent) == [f"aoe stance u2 {stance}"]


def test_an_unknown_stance_or_object_sends_nothing():
    for e in (dict(time=0, player=1, kind="stance", objects=[8], stance="Hold Fire"),
              dict(time=0, player=1, kind="stance", objects=[99], stance="Defensive"),
              dict(time=0, player=1, kind="stance", objects=[8])):
        _, sent, _ = play([e], (MIL, HOUSE))                           # the replay goes on
        assert not stances(sent)


def test_vanilla_has_no_stance():
    d = data([dict(time=0, player=1, kind="stance", objects=[8], stance="Defensive")])
    d["objects"] += [MIL, HOUSE]
    game = replay.Replay(Fake(), d)
    assert game.commands(d["timeline"][0]) == []
