"""game/combat.py: the Castle and Imperial Age upgrades of the military lines have their AoE2 DE values (#1004)."""
import re

from game import combat

UPGRADES = ["CAPPED_RAM", "EAGLE_SCOUT", "EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR", "HAND_CANNONEER", "HEAVY_CAMEL_RIDER",
            "HEAVY_CAVALRY_ARCHER", "HEAVY_SCORPION", "HUSSAR", "IMPERIAL_CAMEL_RIDER", "IMPERIAL_SKIRMISHER", "ONAGER",
            "PETARD", "SIEGE_ONAGER", "SIEGE_RAM"]


def test_each_upgrade_has_values_and_a_valid_stats_command():
    for name in UPGRADES:
        s = combat.STATS[name]
        assert s.hp > 0 and s.attack > 0 and s.reload > 0, name
        assert re.fullmatch(r"aoe stats u \d+ \d+ -?\d+ \d+ [012] [\w,-]+ [\w:,-]+ \d+", combat.stats_command("u", name)), name


def test_values_of_the_wiki():
    assert combat.STATS["HUSSAR"] == combat.Stats(75, 7, 0, 2, 0, 1.9, {}, (combat.CAV,))
    assert combat.STATS["HAND_CANNONEER"] == combat.Stats(40, 17, 1, 0, 7, 3.45, {combat.INF: 10, combat.SPE: 1},
                                                          (combat.ARC, combat.GUN))   # wiki class "Gunpowder Units" (#1007)
    assert combat.STATS["SIEGE_RAM"].pierce == 195 and combat.STATS["SIEGE_RAM"].bonus["building"] == 200


def test_the_upgrade_is_stronger_than_its_base_unit():
    for base, up in [("LIGHT_CAVALRY", "HUSSAR"), ("CAMEL_RIDER", "HEAVY_CAMEL_RIDER"), ("MANGONEL", "ONAGER"),
                     ("ONAGER", "SIEGE_ONAGER"), ("BATTERING_RAM", "CAPPED_RAM"), ("CAPPED_RAM", "SIEGE_RAM"),
                     ("SCORPION", "HEAVY_SCORPION"), ("CAVALRY_ARCHER", "HEAVY_CAVALRY_ARCHER"),
                     ("EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR"), ("ELITE_SKIRMISHER", "IMPERIAL_SKIRMISHER")]:
        assert combat.STATS[up].hp >= combat.STATS[base].hp and combat.STATS[up].attack >= combat.STATS[base].attack, up


def test_a_hand_cannoneer_kills_infantry_fast():
    """AoE2: 17 pierce + 10 against infantry, a Champion has 1 pierce armor: 26 per shot."""
    assert combat.damage("HAND_CANNONEER", "CHAMPION") == 26
