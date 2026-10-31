"""game/combat.py: the castle units Arambai to Keshik fight with their AoE2 DE values (#1005, epic #395)."""
import re

from game import combat

UNITS = ("ARAMBAI", "BALLISTA_ELEPHANT", "BOYAR", "CAMEL_ARCHER", "CENTURION", "COMPOSITE_BOWMAN", "CONQUISTADOR",
         "COUSTILLIER", "GBETO", "GENOESE_CROSSBOWMAN", "GHULAM", "HUSSITE_WAGON", "JAGUAR_WARRIOR", "KAMAYUK",
         "KARAMBIT_WARRIOR", "KESHIK")


def test_each_unit_has_values_and_is_a_unique_unit():
    for name in UNITS:
        assert name in combat.STATS and combat.stats(name) != combat.DEFAULT, name
        assert combat.UNI in combat.stats(name).classes, name


def test_a_valid_stats_command_for_each_unit():
    for name in UNITS:
        cmd = combat.stats_command("u", name)
        assert re.fullmatch(r"aoe stats u \d+ \d+ -?\d+ -?\d+ [012] [a-z_,]+ (-|([a-z_]+:\d+,?)+) \d+( [a-z]+=\S+)*", cmd), cmd
        assert (cmd.split()[7] == "2") == (name in combat.MELEE_RANGED), name   # a thrown melee attack (#800)
