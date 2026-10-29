"""The base unique units of game/combat.py fight with the values of their AoE2 wiki infobox (#1041): DE, no upgrades,
no civilization bonus. The values are lines in game/data/units.jsonl (tests/test_data_files.py, #1916)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402


def test_the_janissary_hits_a_ram_only_with_its_bonus():
    a = combat.stats("JANISSARY")                                      # the high pierce armor: only the bonus hits
    assert combat.damage("JANISSARY", "BATTERING_RAM") == combat.damage("JANISSARY", "BATTERING_RAM", a=a._replace(attack=0))
