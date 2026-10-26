"""game/combat.py: the regional military units fight with their AoE2 DE values (#1007)."""
import re

from game import combat

REGIONAL = ("BATTLE_ELEPHANT", "CONDOTTIERO", "ELITE_BATTLE_ELEPHANT", "ELITE_GENITOUR", "ELITE_STEPPE_LANCER",
            "ELITE_WAR_ELEPHANT", "FLAMING_CAMEL", "GENITOUR", "SLINGER", "STEPPE_LANCER", "WINGED_HUSSAR")
COMMAND = re.compile(r"aoe stats u \d+ \d+ -?\d+ \d+ [012] [a-z,]+ ([a-z]+:\d+(,[a-z]+:\d+)*|-) \d+$")


def test_each_regional_unit_has_values_and_a_valid_command():
    for name in REGIONAL:
        s = combat.STATS[name]
        assert combat.stats(name) is s and s.hp > 0 and s.attack > 0 and s.reload > 0 and s.classes, name
        assert COMMAND.match(combat.stats_command("u", name)), name


def test_values_of_the_wiki():
    # Battle Elephant (melee) and Slinger (ranged): the AoE2 wiki infobox of 2026-10-26.
    assert combat.stats("BATTLE_ELEPHANT") == combat.Stats(250, 12, 1, 2, 0, 2.0, {"building": 4}, (combat.ELE,))
    assert combat.stats("SLINGER") == combat.Stats(35, 4, 0, 0, 5, 2.0, {"infantry": 4, "siege": 3, "spearman": 1},
                                                   (combat.ARC,))


def test_gunpowder_bonus_hits_the_gunpowder_units():
    assert combat.damage("CONDOTTIERO", "JANISSARY") == 10 - 1 + 10
    assert combat.damage("WINGED_HUSSAR", "BOMBARD_CANNON") == 9 - 2 + 4
    assert combat.damage("SLINGER", "MILITIA") == 4 - 1 + 4
