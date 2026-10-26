"""AoE2 DE values of the military units of the DLCs Dynasties of India, Return of Rome and The Three Kingdoms (#1009)."""
import re

from game import combat

UNITS = ("ARMORED_ELEPHANT", "FIRE_LANCER", "GRENADIER", "HEI_GUANG_CAVALRY", "IRON_PAGODA", "LEGIONARY",
         "ROCKET_CART", "SIEGE_ELEPHANT", "TRACTION_TREBUCHET", "WHITE_FEATHER_GUARD")


def test_each_unit_has_values_and_a_valid_command():
    for name in UNITS:
        assert name in combat.STATS, name
        cmd = combat.stats_command("u", name)
        assert re.fullmatch(r"aoe stats u \d+ \d+ -?\d+ \d+ [012] [a-z,]+ (-|[a-z]+:\d+(,[a-z]+:\d+)*) \d+", cmd), cmd


def test_two_units_have_the_values_of_the_wiki():
    lancer = combat.stats("FIRE_LANCER")                              # melee: 65 HP, 9 attack, 1/0 armor
    assert (lancer.hp, lancer.attack, lancer.melee, lancer.pierce, lancer.range, lancer.reload) == (65, 9, 1, 0, 0, 2.0)
    assert lancer.bonus == {"building": 1, combat.CAV: 5, combat.CAM: 4, combat.ELE: 5}
    treb = combat.stats("TRACTION_TREBUCHET")                         # siege: 50 melee damage from range 14
    assert (treb.hp, treb.attack, treb.melee, treb.pierce, treb.range, treb.reload) == (115, 50, 1, 8, 14, 11.0)
    assert treb.bonus == {"building": 230} and combat.stats_command("u", "TRACTION_TREBUCHET").split()[7] == "2"


def test_a_siege_elephant_takes_more_from_a_melee_hit():
    assert combat.damage("MILITIA", "SIEGE_ELEPHANT") == 4 + 2            # melee armor -2, as a ram
