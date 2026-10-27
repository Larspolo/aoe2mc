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


def test_values_of_the_wiki():
    """AoE2 wiki (DE): Elite Cataphract 150 HP, 12 attack, 2/1 armor, +18 vs infantry, reload 1.7; Elite Longbowman
    40 HP, 7 attack, range 6, 0/1 armor, +2 vs spearmen."""
    s = combat.stats("ELITE_LONGBOWMAN")
    assert (s.hp, s.attack, s.melee, s.pierce, s.range, s.bonus) == (40, 7, 0, 1, 6, {combat.SPE: 2})
    assert combat.damage("ELITE_CATAPHRACT", "MILITIA") == 12 - 0 + 18
    assert combat.damage("ELITE_LONGBOWMAN", "SPEARMAN") == 7 - 0 + 2


def test_a_valid_stats_command_for_each_unit():
    for name in UNITS:
        cmd = combat.stats_command("u", name)
        assert re.fullmatch(r"aoe stats u \d+ \d+ -?\d+ -?\d+ [012] [a-z,]+ (-|([a-z]+:\d+,?)+) \d+", cmd), cmd
    for name in ("ELITE_GBETO", "ELITE_MAMELUKE", "ELITE_THROWING_AXEMAN"):      # a thrown melee attack, as the base unit
        assert combat.stats_command("u", name).split()[7] == "2", name
    assert combat.stats_command("u", "ELITE_KAMAYUK").split()[7] == "0"         # melee
