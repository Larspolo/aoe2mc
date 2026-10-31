"""game/combat.py: the regional military units fight with their AoE2 DE values (#1007)."""
import re

from game import combat

REGIONAL = ("BATTLE_ELEPHANT", "CONDOTTIERO", "ELITE_BATTLE_ELEPHANT", "ELITE_GENITOUR", "ELITE_STEPPE_LANCER",
            "ELITE_WAR_ELEPHANT", "FLAMING_CAMEL", "GENITOUR", "SLINGER", "STEPPE_LANCER", "WINGED_HUSSAR")
COMMAND = re.compile(r"aoe stats u \d+ \d+ -?\d+ \d+ [012] [a-z_,]+ ([a-z_]+:\d+(,[a-z_]+:\d+)*|-) \d+( [a-z]+=\S+)*$")


def test_each_regional_unit_has_values_and_a_valid_command():
    for name in REGIONAL:
        s = combat.STATS[name]
        assert combat.stats(name) is s and s.hp > 0 and s.attack > 0 and s.reload > 0 and s.classes, name
        assert COMMAND.match(combat.stats_command("u", name)), name
