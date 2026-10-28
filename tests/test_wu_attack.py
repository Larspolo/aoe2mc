"""game/civs.py UNITS: the Wu Jian Swordsmen and Hei Guang Cavalry have +2 attack in the Imperial Age, as in AoE2 DE
(#2312, wiki "Wu"). The group "jian swordsmen, hei guang cavalry" is the key "groups" of their lines in units.jsonl."""
import types

import pytest

from game import civs, combat

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, age=3):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(AGES[:age]))


@pytest.mark.parametrize("name", ["JIAN_SWORDSMAN", "HEI_GUANG_CAVALRY", "HEAVY_HEI_GUANG_CAVALRY"])
def test_wu_units_have_2_more_attack_in_the_imperial_age(name):
    base = combat.stats(name)
    assert civs.units(game("WU", 3), name, base) == base._replace(attack=base.attack + 2)
    for age in (0, 1, 2):
        assert civs.units(game("WU", age), name, base) == base, age
    assert civs.units(game("SHU"), name, base).attack == base.attack          # no bonus for another civilization


def test_other_wu_units_have_no_attack_bonus():
    for name in ("KNIGHT", "MAN_AT_ARMS", "ARCHER"):
        assert civs.units(game("WU"), name, combat.stats(name)).attack == combat.stats(name).attack, name
