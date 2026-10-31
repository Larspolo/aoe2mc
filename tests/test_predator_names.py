"""The predators of a real scenario (the AoE2ScenarioParser names) get their AoE2 combat values (#3623)."""
from AoE2ScenarioParser.datasets.units import UnitInfo

from game import combat, gather


def test_each_predator_of_the_parser_has_combat_values():
    names = [u.name for u in UnitInfo if gather.predator(u.name) and "TREBUCHET" not in u.name]
    assert names
    assert [n for n in names if combat.stats(n) is combat.DEFAULT] == []

