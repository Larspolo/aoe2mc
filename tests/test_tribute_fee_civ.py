"""The tribute fee of a civilization (#4445): Palmyrans send tributes with no fee ("Tributes are not taxed", Return of
Rome), and another civilization pays diplomacy.FEE."""
from test_tribute import setup

from game import diplomacy

civs = diplomacy.civs   # the module that diplomacy reads (its own import path, not game.civs)


def test_a_civilization_with_no_tribute_fee_pays_no_fee(monkeypatch):
    server, g = setup()
    monkeypatch.setattr(civs, "civ", lambda g, player=None: "PALMYRANS")
    monkeypatch.setitem(civs.BY_KEY, "tribute_fee", {"PALMYRANS": 0})
    assert diplomacy.fee(g) == 0
    assert diplomacy.cost(g, 100) == 100


def test_another_civilization_pays_the_tribute_fee(monkeypatch):
    server, g = setup()
    monkeypatch.setattr(civs, "civ", lambda g, player=None: "BRITONS")
    monkeypatch.setitem(civs.BY_KEY, "tribute_fee", {"PALMYRANS": 0})
    assert diplomacy.fee(g) == diplomacy.FEE
    assert diplomacy.cost(g, 100) == 100 + diplomacy.FEE
