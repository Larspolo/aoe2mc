"""The hero siege units of the campaigns are siege units too: a minecart with a crew (#3020)."""
import units
from game import ai

HEROES = ("JEAN_BUREAU", "JEAN_DE_LORRAIN", "BAD_NEIGHBOR", "BAD_NEIGHBOR_PACKED", "GODS_OWN_SLING",
          "GODS_OWN_SLING_PACKED", "WARWOLF_TREBUCHET", "WARWOLF_TREBUCHET_PACKED")


def test_hero_siege_units_are_siege_units():
    assert all(units.siege(n) for n in HEROES)


def test_the_speed_of_a_hero_siege_unit_goes_through_the_plugin():
    assert ai.speed_command("u", "JEAN_BUREAU", 4).startswith("aoe speed ")
