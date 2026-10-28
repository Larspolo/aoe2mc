"""The name tags of the heroes keep their Roman numerals and particles (#3059); the variant letters of other units stay out."""
import numpy as np
import pytest

import units


@pytest.mark.parametrize("name, text", [
    ("HENRY_V", "Henry V"),
    ("POPE_LEO_I", "Pope Leo I"),
    ("SURYAVARMAN_I", "Suryavarman I"),
    ("UDAYADITYAVARMAN_I", "Udayadityavarman I"),
    ("EMPEROR_IN_A_BARREL", "Emperor in a Barrel"),
    ("EMPEROR_IN_A_LITTER", "Emperor in a Litter"),
    ("DUKE_D_ALENCON", "Duke d'Alencon"),
    ("BERNARD_D_ARMAGNAC", "Bernard d'Armagnac"),
])
def test_hero_keeps_its_name(name, text):
    assert units.pretty(name, hero=True) == text


@pytest.mark.parametrize("name, text", [
    ("COW_A", "Cow"),
    ("FLAG_I", "Flag"),
    ("WILD_HORSE_C", "Wild Horse"),
    ("TORCH_A_CONVERTABLE", "Torch Convertable"),
])
def test_other_unit_drops_its_variant_letter(name, text):
    assert units.pretty(name) == text


def test_hero_name_tag_has_the_numeral():
    o = dict(name="HENRY_V", hero=True, player=1, rotation=0.0)
    nbt = units.make_entity(o, {}, (0.5, 0.0, 0.5), np.random.default_rng(1))
    assert "Henry V" in str(units.top_entity(nbt)["CustomName"])
