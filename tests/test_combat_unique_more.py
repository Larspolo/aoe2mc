"""game/combat.py: the unique units Kipchak to War Wagon fight with their AoE2 DE values (#1006)."""
import re

import pytest

from game import combat

UNITS = ["KIPCHAK", "KONNIK", "LEITIS", "MAGYAR_HUSZAR", "MONASPA", "OBUCH", "ORGAN_GUN", "PLUMED_ARCHER", "RATHA",
         "RATTAN_ARCHER", "SERJEANT", "SHOTEL_WARRIOR", "SHRIVAMSHA_RIDER", "TARKAN", "URUMI_SWORDSMAN", "WAR_WAGON"]


@pytest.mark.parametrize("unit", UNITS)
def test_each_unit_has_values_and_a_valid_stats_command(unit):
    s = combat.STATS[unit]
    assert s.hp > 0 and s.attack > 0 and s.reload > 0 and combat.UNI in s.classes
    assert re.fullmatch(r"aoe stats u \d+ \d+ \d+ \d+ [01] [a-z,]+ (-|[a-z]+:\d+(,[a-z]+:\d+)*) \d+",
                        combat.stats_command("u", unit))


def test_the_values_of_the_wiki():
    assert combat.STATS["TARKAN"] == combat.Stats(100, 8, 1, 3, 0, 1.9, {"building": 8}, ("cavalry", "unique"))
    assert combat.STATS["WAR_WAGON"] == combat.Stats(150, 9, 0, 2, 4, 2.5, {"building": 2},
                                                     ("archer", "cavalry", "unique"))
    assert combat.damage("MAGYAR_HUSZAR", "MANGONEL") == 10 - 0 + 5      # its bonus against siege weapons
