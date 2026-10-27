"""game/combat.py: the siege units fight with the values of their AoE2 DE wiki infobox (#1402): the lines of
game/data/units.jsonl (tests/test_data_files.py, #1916)."""
from game import combat
from game.combat import CAV, ELE, HSI, RAM, SIE, UNI


def test_the_damage_type_of_each_siege_unit():
    # the mangonel line and the bombard cannon do melee damage, the scorpion and the trebuchet pierce damage
    assert {"BOMBARD_CANNON", "MANGONEL", "ONAGER", "SIEGE_ONAGER"} <= combat.MELEE_RANGED
    assert not {"HEAVY_SCORPION", "SCORPION", "TREBUCHET"} & combat.MELEE_RANGED
    assert combat.damage("TREBUCHET", "BARRACKS") == 200 - 7 + 250
    assert combat.damage("BOMBARD_CANNON", "BARRACKS") == 40 - 0 + 200


def test_the_new_classes_give_the_bonus():
    assert HSI in combat.STATS["HUSSITE_WAGON"].classes and HSI in combat.STATS["ELITE_BALLISTA_ELEPHANT"].classes
    assert (CAV, ELE, SIE, UNI, HSI) == combat.STATS["BALLISTA_ELEPHANT"].classes
    assert RAM in combat.STATS["SIEGE_ELEPHANT"].classes
    # a mangonel hits a hussite wagon with its melee attack and the siege and heavy siege bonus
    assert combat.damage("MANGONEL", "HUSSITE_WAGON") == 40 - 0 + 12 + 40
    # a scorpion bolt: its pierce attack, the pierce armor of the target and the infantry bonus
    assert combat.damage("SCORPION", "MILITIA") == 11 - 1 + 1
    assert "heavysiege" in combat.stats_command("u", "HUSSITE_WAGON").split()[8]
