"""The flares of a record with a view player (#2403, epic #2401): `--view N` shows only the flares that player N
receives, as the AoE2 replay of one player; without a view all flares show."""
import os

import pytest
from test_replay import Fake, data

import aoe2mc
from game import replay

RECORD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-63.0.aoe2record")
FLARE = {"time": 5000, "player": 1, "kind": "flare", "tile": [2.0, 2.0], "to": [1, 3]}


def shown(pov, e=FLARE):
    r = replay.Replay(Fake(), data([]), pov=pov)
    return bool(r.commands(e)) and r.flares != []


@pytest.mark.skipif(not os.path.isfile(RECORD), reason="no sample record")
def test_the_flares_of_a_record_have_their_receivers():
    flares = [e for e in aoe2mc.read_timeline(RECORD) if e["kind"] == "flare"]
    assert [(e["player"], e["to"]) for e in flares[:2]] == [(2, [2, 4]), (1, [1, 3])]   # the teams 1, 3 and 2, 4


def test_a_flare_to_player_1_shows_with_view_1_and_not_with_view_3():
    assert shown(1) and shown(3) and not shown(2) and not shown(4)


def test_all_flares_show_without_a_view():
    assert shown(None) and shown(None, dict(FLARE, to=[]))


def test_the_sender_sees_its_own_flare():
    assert shown(1, dict(FLARE, to=[3])) and not shown(2, dict(FLARE, to=[3]))
