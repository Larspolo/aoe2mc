"""game/train.py stats and game/civs.py SMITH_UNITS: the blacksmith bonuses of the Incas, Macedonians and Romans (#2174).
Values: the AoE2 DE wiki, civilization pages: "Villagers benefit from Blacksmith infantry technologies starting in the
Castle Age." (Incas), "Infantry armor upgrades also benefit cavalry." (Macedonians), "Infantry receives double the effect
from Blacksmith armor upgrades." (Romans)."""
import pytest
from test_forging import setup

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def player(civ, ages, *techs):
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs = set(ages) | set(techs)
    return server, g


def change(civ, unit, ages=CASTLE, techs=("FORGING", "SCALE_MAIL_ARMOR")):
    """The (attack, melee, pierce) change of unit from techs."""
    a, b = train.stats(player(civ, ages)[1], unit), train.stats(player(civ, ages, *techs)[1], unit)
    return b.attack - a.attack, b.melee - a.melee, b.pierce - a.pierce


def test_an_inca_villager_gets_the_infantry_technologies_from_the_castle_age():
    assert change("INCAS", "VILLAGER_MALE") == (1, 1, 1)
    assert change("INCAS", "VILLAGER_MALE", ages=("FEUDAL_AGE",)) == (0, 0, 0)


def test_a_macedonian_knight_gets_the_infantry_armor():
    assert change("MACEDONIANS", "KNIGHT", techs=("SCALE_MAIL_ARMOR", "CHAIN_MAIL_ARMOR")) == (0, 2, 2)


def test_a_roman_militia_gets_twice_the_infantry_armor():
    assert change("ROMANS", "MILITIA", techs=("SCALE_MAIL_ARMOR",)) == (0, 2, 2)
    assert change("ROMANS", "MILITIA", techs=("FORGING",)) == (1, 0, 0)                 # the attack once


@pytest.mark.parametrize("unit, normal", [("VILLAGER_MALE", (0, 0, 0)), ("KNIGHT", (1, 0, 0)), ("MILITIA", (1, 1, 1))])
@pytest.mark.parametrize("civ", ["BRITONS", "INCAS", "MACEDONIANS", "ROMANS"])
def test_other_civilizations_and_units_keep_the_normal_effect(civ, unit, normal):
    if (civ, unit) not in {("INCAS", "VILLAGER_MALE"), ("MACEDONIANS", "KNIGHT"), ("ROMANS", "MILITIA")}:
        assert change(civ, unit) == normal


def test_the_live_inca_villager_gets_the_values_at_the_castle_age():
    server, g = player("INCAS", ("FEUDAL_AGE",), "FORGING")
    g.units.append({"uuid": "v", "name": "VILLAGER_MALE"})
    train.research(g, {"name": "CASTLE_AGE", "player": "Steve"})
    s = train.stats(g, "VILLAGER_MALE")
    assert s.attack == combat.stats("VILLAGER_MALE").attack + 1
    assert combat.stats_command("v", "VILLAGER_MALE", s) in server.log
