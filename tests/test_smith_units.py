"""game/train.py stats and game/civs.py SMITH_UNITS: the blacksmith bonuses of the Incas, Macedonians and Romans (#2174).
Values: the AoE2 DE wiki, civilization pages: "Villagers benefit from Blacksmith infantry technologies starting in the
Castle Age." (Incas), "Infantry armor upgrades also benefit cavalry." (Macedonians), "Infantry receives double the effect
from Blacksmith armor upgrades." (Romans)."""
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
    assert change("INCAS", "VILLAGER_MALE") == change("INCAS", "MILITIA") != (0, 0, 0)
    assert change("INCAS", "VILLAGER_MALE", ages=("FEUDAL_AGE",)) == change("BRITONS", "VILLAGER_MALE", ages=("FEUDAL_AGE",))


def test_a_macedonian_knight_gets_the_infantry_armor():
    armor = ("SCALE_MAIL_ARMOR", "CHAIN_MAIL_ARMOR")
    assert change("MACEDONIANS", "KNIGHT", techs=armor) == change("BRITONS", "MILITIA", techs=armor) != (0, 0, 0)


def test_a_roman_militia_gets_twice_the_infantry_armor():
    a, m, p = change("BRITONS", "MILITIA", techs=("SCALE_MAIL_ARMOR",))
    assert change("ROMANS", "MILITIA", techs=("SCALE_MAIL_ARMOR",)) == (a, 2 * m, 2 * p) and (m, p) != (0, 0)
    assert change("ROMANS", "MILITIA", techs=("FORGING",)) == change("BRITONS", "MILITIA", techs=("FORGING",))   # the attack once


def test_the_live_inca_villager_gets_the_values_at_the_castle_age():
    server, g = player("INCAS", ("FEUDAL_AGE",), "FORGING")
    g.units.append({"uuid": "v", "name": "VILLAGER_MALE"})
    train.research(g, {"name": "CASTLE_AGE", "player": "Steve"})
    s = train.stats(g, "VILLAGER_MALE")
    assert s == train.stats(player("INCAS", CASTLE, "FORGING")[1], "VILLAGER_MALE") != combat.stats("VILLAGER_MALE")
    assert combat.stats_command("v", "VILLAGER_MALE", s) in server.log
