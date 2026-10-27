"""game/combat.py: the siege units have the values of their AoE2 DE wiki infobox (#1402)."""
from game import combat
from game.combat import CAV, ELE, GUN, HSI, INF, RAM, SIE, UNI, Stats

# hit points, attack, melee armor, pierce armor, range, reload, bonus, classes (MediaWiki API, 2026-10-27)
WIKI = {
    "BATTERING_RAM": Stats(175, 2, -3, 180, 0, 5.0, {"building": 150, SIE: 40}, (SIE, RAM)),
    "BOMBARD_CANNON": Stats(80, 40, 2, 5, 12, 6.5, {"building": 200, HSI: 40, SIE: 20}, (GUN, SIE)),
    "CAPPED_RAM": Stats(200, 3, -2, 190, 0, 5.0, {"building": 160, SIE: 50}, (SIE, RAM)),
    "HEAVY_SCORPION": Stats(60, 14, 1, 8, 7, 3.6, {"building": 6, ELE: 10, INF: 2, RAM: 2}, (SIE,)),
    "MANGONEL": Stats(50, 40, 0, 6, 7, 6.0, {"building": 35, HSI: 40, SIE: 12}, (SIE,)),
    "ONAGER": Stats(60, 55, 0, 8, 8, 6.0, {"building": 45, HSI: 50, SIE: 12}, (SIE,)),
    "SCORPION": Stats(40, 11, 0, 7, 7, 3.6, {"building": 3, ELE: 7, INF: 1, RAM: 1}, (SIE,)),
    "SIEGE_ONAGER": Stats(70, 75, 0, 8, 8, 6.0, {"building": 60, HSI: 50, SIE: 12}, (SIE,)),
    "SIEGE_RAM": Stats(270, 4, -1, 195, 0, 5.0, {"building": 200, SIE: 65}, (SIE, RAM)),
    "SIEGE_TOWER": Stats(175, 0, -2, 100, 0, 0.0, {}, (SIE, RAM)),
    "TREBUCHET": Stats(150, 200, 1, 150, 16, 10.0, {"building": 250}, (SIE, RAM)),     # unpacked
}


def test_each_siege_unit_has_its_wiki_values():
    for name, s in WIKI.items():
        assert combat.STATS[name] == s, name


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
