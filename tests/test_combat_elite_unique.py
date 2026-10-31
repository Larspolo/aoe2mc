"""game/combat.py: the elite unique units fight with their AoE2 DE values (#1008, epic #395)."""
import re

from AoE2ScenarioParser.datasets.units import UnitInfo

from game import combat, train

UNITS = sorted(f"ELITE_{u}" for u in set(train.UNIQUE.values()) if f"ELITE_{u}" in UnitInfo.__members__)


def test_each_elite_unique_unit_has_values():
    assert UNITS
    for name in UNITS:
        assert name in combat.STATS and combat.UNI in combat.stats(name).classes, name
        base, elite = combat.stats(name[6:]), combat.stats(name)
        assert elite.classes == base.classes and elite.hp >= base.hp, name


def test_a_valid_stats_command_for_each_unit():
    for name in UNITS:
        cmd = combat.stats_command("u", name)
        assert re.fullmatch(r"aoe stats u \d+ \d+ -?\d+ -?\d+ [012] [a-z,]+ (-|([a-z]+:\d+,?)+) \d+( [a-z]+=\S+)*", cmd), cmd
        assert (cmd.split()[7] == "2") == (name in combat.MELEE_RANGED), name   # a thrown melee attack
