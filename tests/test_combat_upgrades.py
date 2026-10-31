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

