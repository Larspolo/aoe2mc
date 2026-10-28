"""Live replay on Paper: the ATTACK MOVE action of the record walks the group to the tile, and its military units
take the aggressive stance for the walk (#2552). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL, orders, play  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402

GO = dict(time=1000, player=1, kind="attack_move", objects=[7, 8], tile=[12.5, 3.5],
          names=["VILLAGER_MALE", "MILITIA"])


def stances(sent):
    return [c for c in sent if c.startswith("aoe stance ")]


def test_an_attack_move_walks_the_group_and_makes_the_military_aggressive():
    _, sent, _ = play([GO], (VIL, MIL, HOUSE))
    assert {"u1", "u2"} <= set(orders(sent))                           # both walk to the tile
    assert stances(sent) == ["aoe stance u2 aggressive"]


def test_a_villager_in_the_group_only_walks():
    _, sent, _ = play([dict(GO, objects=[7], names=["VILLAGER_MALE"])], (VIL, MIL, HOUSE))
    assert "u1" in orders(sent) and not stances(sent)


def test_the_stance_of_the_record_comes_back_at_the_end_of_the_walk():
    stand = dict(time=0, player=1, kind="stance", objects=[8], stance="Stand Ground")
    r, sent, _ = play([stand, GO], (VIL, MIL, HOUSE))
    assert stances(sent) == ["aoe stance u2 stand_ground", "aoe stance u2 aggressive", "aoe stance u2 stand_ground"]
    assert not r.charging


def test_vanilla_walks_with_no_stance():
    d = data([GO])
    d["objects"] += [VIL, MIL, HOUSE]
    game = replay.Replay(Fake(), d)
    assert not stances(game.commands(d["timeline"][0])) and game.moving
