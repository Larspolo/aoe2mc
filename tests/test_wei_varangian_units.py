"""game/civs.py UNITS and COSTS: the unique unit bonuses of the Wei and the Varangians, as in AoE2 DE (#2246): Wei Hei
Guang Cavalry +20 %/30 % hit points in the Castle/Imperial Age, Wei Traction Trebuchets and Lou Chuans cost -25 %,
Varangian Guards attack 25 % faster (the reload / 1.25)."""
import types

import pytest

from game import civs, combat, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, age=3):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(AGES[:age]))


@pytest.mark.parametrize("name", ["HEI_GUANG_CAVALRY", "HEAVY_HEI_GUANG_CAVALRY"])
def test_wei_hei_guang_cavalry_has_more_hit_points_in_the_castle_and_imperial_age(name):
    base = combat.stats(name)
    for age, factor in ((1, 1), (2, 1.2), (3, 1.3)):
        assert civs.units(game("WEI", age), name, base).hp == round(base.hp * factor), (name, age)
    assert civs.units(game("SHU"), name, base) == base


@pytest.mark.parametrize("name", ["LOU_CHUAN", "TRACTION_TREBUCHET"])
def test_wei_traction_trebuchets_and_lou_chuans_cost_25_percent_less(name):
    base = train.COSTS[name]
    assert civs.cost(game("WEI"), name, base) == {r: round(v * 0.75) for r, v in base.items()}
    assert civs.cost(game("SHU"), name, base) == base                             # Shu: no cost bonus for these


@pytest.mark.parametrize("name", ["VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD"])
def test_varangian_guards_attack_25_percent_faster(name):
    base = combat.stats(name)
    assert civs.units(game("VARANGIANS", 0), name, base).reload == pytest.approx(base.reload / 1.25)
    assert civs.units(game("WEI"), name, base) == base


def test_other_units_of_the_wei_and_varangians_do_not_change():
    for civ, name in (("WEI", "KNIGHT"), ("WEI", "TREBUCHET"), ("VARANGIANS", "MAN_AT_ARMS")):
        assert civs.units(game(civ), name, combat.stats(name)) == combat.stats(name), (civ, name)
    assert civs.cost(game("WEI"), "TREBUCHET", train.COSTS["TREBUCHET"]) == train.COSTS["TREBUCHET"]
