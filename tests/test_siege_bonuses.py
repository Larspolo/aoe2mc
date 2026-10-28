"""game/civs.py: the Macedonian siege weapons have +1 pierce armor and +30 % attack against buildings, and the Wei
traction trebuchets and lou chuans cost 25 % less (AoE2 DE, #2272)."""
from game import train

from test_civ_work import setup


def test_a_macedonian_mangonel_has_more_pierce_armor_and_more_attack_against_buildings():
    mace, frank = train.stats(setup("MACEDONIANS"), "MANGONEL"), train.stats(setup("FRANKS"), "MANGONEL")
    assert (mace.pierce, frank.pierce) == (7, 6)
    assert (mace.bonus["building"], frank.bonus["building"]) == (46, 35)  # 35 × 1.3 = 45.5, AoE2 rounds half up
    assert mace.bonus["siege"] == frank.bonus["siege"]


def test_a_wei_traction_trebuchet_costs_25_percent_less():
    base = train.COSTS["TRACTION_TREBUCHET"]
    assert train.price(setup("WEI"), "TRACTION_TREBUCHET") == {r: int(n * 0.75 + 0.5) for r, n in base.items()}
