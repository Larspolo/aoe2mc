"""Heroes and siege units with an animal word in the name are no animals (#3626)."""
import pytest

import units
from game import gather

NOT_ANIMALS = ["HENRY_THE_LION", "RICHARD_THE_LIONHEART", "WARWOLF_TREBUCHET", "WARWOLF_TREBUCHET_PACKED"]


@pytest.mark.parametrize("name", NOT_ANIMALS)
def test_hero_and_siege_are_no_animal(name):
    assert units.animal(name) is None
    assert units.classify(name, hero="TREBUCHET" not in name)["id"] != "minecraft:wolf"
    assert gather.military(name)


@pytest.mark.parametrize("name", ["HUNTING_WOLF", "ORNLU_THE_WOLF", "WHITE_TIGER_YAN", "WOLF"])
def test_real_animals_stay_wolves(name):
    assert units.classify(name)["id"] == "minecraft:wolf"
