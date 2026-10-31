"""game/gather.py CARRY_RATE (#5244): Wheelbarrow and Hand Cart multiply the carry of a villager, as the .dat of AoE2 DE.
Test data, not the data line (owner, #4242)."""
from test_wheelbarrow import setup

from game import gather


def test_the_carry_techs_multiply_the_carry_of_a_hunter(monkeypatch):
    monkeypatch.setattr(gather, "CARRY_RATE", {"WHEELBARROW": 1.2, "HAND_CART": 1.5})
    server, g = setup()
    g.carry = 35                                                   # a hunter of the .dat
    assert g.limit("wood") == 35
    g.techs.add("WHEELBARROW")
    assert g.limit("wood") == 42
    g.techs.add("HAND_CART")
    assert g.limit("wood") == 63


def test_the_civ_bonus_adds_after_the_factor(monkeypatch):
    monkeypatch.setattr(gather, "CARRY_RATE", {"WHEELBARROW": 2})
    server, g = setup()
    base = g.limit("wood")
    g.techs.add("WHEELBARROW")
    assert g.limit("wood") == 2 * base
