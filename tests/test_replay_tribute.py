"""Live replay: a tribute of the record moves the resources of the estimate (#3940): the sender pays the amount and
the fee, the receiver gets the amount. Coinage lowers the fee."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import diplomacy  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

S = replay.START


def paid(fee, n=100):
    """What the sender pays for a tribute of n with the fee in percent."""
    return n * (100 + fee) // 100


def make():
    return replay.Replay(Fake(), data([]))


def test_a_tribute_takes_the_amount_and_the_fee_from_the_sender():
    r = make()
    r.commands({"time": 200_000, "player": 1, "kind": "tribute", "to": 2, "food": 100, "wood": 0, "gold": 0, "stone": 0})
    assert r.resources(1)["food"] == S["food"] - paid(diplomacy.FEE)
    assert r.resources(2)["food"] == S["food"] + 100


def test_coinage_lowers_the_fee_of_the_tribute():
    r = make()
    r.commands({"time": 100_000, "player": 1, "kind": "research", "technology": "Coinage"})
    r.commands({"time": 200_000, "player": 1, "kind": "tribute", "to": 2, "food": 100, "wood": 0, "gold": 0, "stone": 0})
    assert r.resources(1)["food"] == S["food"] - paid(diplomacy.FEES["COINAGE"]) > S["food"] - paid(diplomacy.FEE)
    assert r.resources(2)["food"] == S["food"] + 100


def test_an_old_record_moves_its_one_resource():
    r = make()
    r.commands({"time": 200_000, "player": 1, "kind": "tribute", "to": 2, "resource": "GOLD", "amount": 100})
    assert r.resources(1)["gold"] == S["gold"] - paid(diplomacy.FEE)
    assert r.resources(2)["gold"] == S["gold"] + 100
