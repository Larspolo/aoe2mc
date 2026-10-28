"""game/civs.py UNITS: a Wei Xianbei Raider has +20 % hit points in the Castle Age and +30 % in the Imperial Age, as in
AoE2 DE (#2486)."""
import types

from game import civs, combat

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, age=3):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(AGES[:age]))


def test_a_wei_xianbei_raider_has_more_hit_points_in_the_castle_and_imperial_age():
    base = combat.stats("XIANBEI_RAIDER")
    for age, factor in ((1, 1), (2, 1.2), (3, 1.3)):
        assert civs.units(game("WEI", age), "XIANBEI_RAIDER", base).hp == round(base.hp * factor), age
    assert civs.units(game("SHU"), "XIANBEI_RAIDER", base) == base
