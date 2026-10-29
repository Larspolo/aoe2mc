"""game/civs.py: the civilization bonuses of the attack against a class (#2249, AoE2 DE wiki): Bengali cavalry against
skirmishers, Japanese mounted archers against archers but not skirmishers, Goth infantry against the standard buildings,
more in each age. The value "bonus:CLASS" of the key "units" (civs.UNITS)."""
from test_civ_costs import setup

from game import combat, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def bonus(civ, attacker, target, age=2):
    """The bonus attack of a unit of civ against target in age 0 (Dark) .. 3 (Imperial): combat.damage's sum."""
    _, g = setup(civ, feudal=False)
    g.techs.update(AGES[:age])
    return sum(train.stats(g, attacker).bonus.get(c, 0) for c in combat.stats(target).classes)


def test_a_bengali_knight_has_more_attack_against_a_skirmisher():
    assert bonus("BENGALIS", "KNIGHT", "SKIRMISHER") > bonus("BRITONS", "KNIGHT", "SKIRMISHER")
    assert bonus("BENGALIS", "KNIGHT", "ELITE_SKIRMISHER") > bonus("BRITONS", "KNIGHT", "ELITE_SKIRMISHER")
    assert bonus("BENGALIS", "KNIGHT", "ARCHER") == bonus("BRITONS", "KNIGHT", "ARCHER")
    assert bonus("BENGALIS", "MILITIA", "SKIRMISHER") == bonus("BRITONS", "MILITIA", "SKIRMISHER")   # not infantry


def test_a_japanese_cavalry_archer_has_more_against_an_archer_but_not_a_skirmisher():
    assert bonus("JAPANESE", "CAVALRY_ARCHER", "ARCHER") > bonus("BRITONS", "CAVALRY_ARCHER", "ARCHER")
    assert bonus("JAPANESE", "CAVALRY_ARCHER", "SKIRMISHER") == bonus("BRITONS", "CAVALRY_ARCHER", "SKIRMISHER")
    assert bonus("JAPANESE", "ARCHER", "ARCHER") == bonus("BRITONS", "ARCHER", "ARCHER")   # a foot archer: no


def test_a_goth_man_at_arms_has_more_against_a_house_in_each_age():
    more = [bonus("GOTHS", "MAN_AT_ARMS", "HOUSE", age) - bonus("BRITONS", "MAN_AT_ARMS", "HOUSE", age) for age in range(4)]
    assert more[0] == 0 and all(a < b for a, b in zip(more, more[1:])), more
    assert bonus("GOTHS", "MAN_AT_ARMS", "STONE_WALL") == bonus("BRITONS", "MAN_AT_ARMS", "STONE_WALL")   # no wall
    assert bonus("GOTHS", "KNIGHT", "HOUSE") == bonus("BRITONS", "KNIGHT", "HOUSE")


def test_the_live_command_has_the_bonus():
    _, g = setup("BENGALIS")
    s = train.stats(g, "KNIGHT")
    assert f"skirmisher:{s.bonus['skirmisher']}" in combat.stats_command("k", "KNIGHT", s).split()[9]
