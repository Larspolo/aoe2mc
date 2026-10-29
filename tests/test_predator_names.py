"""The predators of a real scenario (the AoE2ScenarioParser names) get their AoE2 combat values (#3623)."""
from AoE2ScenarioParser.datasets.units import UnitInfo

from game import combat, gather


def test_each_predator_of_the_parser_has_combat_values():
    names = [u.name for u in UnitInfo if gather.predator(u.name) and "TREBUCHET" not in u.name]
    assert names
    assert [n for n in names if combat.stats(n) is combat.DEFAULT] == []


def test_each_parser_name_has_the_values_of_its_animal():
    assert all(combat.stats(a) == combat.stats(b) for a, b in
               (("GREY_WOLF", "WOLF"), ("KOMODO_DRAGON", "KOMODO"), ("BLACK_PANTHER", "PANTHER")))
