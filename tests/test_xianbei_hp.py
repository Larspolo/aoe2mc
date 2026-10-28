"""game/civs.py UNITS: a Wei Xianbei Raider has 36 hit points in the Castle Age and 40 in the Imperial Age, as in
AoE2 DE (#2486; +31.75 % since update 153015, #2843). The Hei Guang Cavalry keeps +20 % and +30 %."""
import types

from game import civs, combat

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, age=3):
    return types.SimpleNamespace(data={"players": {"1": {"civ": civ}}}, player=1, techs=set(AGES[:age]))


def test_a_wei_xianbei_raider_has_more_hit_points_in_the_castle_and_imperial_age():
    base = combat.stats("XIANBEI_RAIDER")
    for age, hp in ((1, 30), (2, 36), (3, 40)):   # numbers of the wiki infobox, not the factor of the data
        assert civs.units(game("WEI", age), "XIANBEI_RAIDER", base).hp == hp, age
    assert civs.units(game("SHU"), "XIANBEI_RAIDER", base) == base


def test_a_wei_hei_guang_cavalry_keeps_30_percent_in_the_imperial_age():
    base = combat.stats("HEI_GUANG_CAVALRY")
    assert [civs.units(game("WEI", age), "HEI_GUANG_CAVALRY", base).hp for age in (1, 2, 3)] == [60, 72, 78]
