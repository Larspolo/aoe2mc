"""Every AoE2 unit and hero gives a valid Minecraft entity (or is skipped on purpose)."""
import os

import numpy as np
import pytest
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

import mcvalid
import units
from conftest import entity_ids

NAMES = sorted({(u.name, False) for u in UnitInfo} | {(h.name, True) for h in HeroInfo})


@pytest.mark.parametrize("name,hero", NAMES)
def test_classify_gives_valid_entities(name, hero):
    desc = units.classify(name, hero)
    if desc is None:
        return
    for eid in entity_ids(desc):
        assert mcvalid.entity_error(eid) is None, (name, eid)


def test_make_entity_has_name_tag_on_the_rider():
    o = dict(name="KNIGHT", hero=False, player=1, rotation=0.0)
    nbt = units.make_entity(o, {1: {"color": "blue"}}, (1.5, 64.0, 2.5), np.random.default_rng(0))
    assert str(nbt["id"]) == "minecraft:horse"
    rider = units.top_entity(nbt)
    assert str(rider["id"]) == "minecraft:zombie"
    assert "Knight" in str(rider["CustomName"])


@pytest.mark.parametrize("name,expected", [
    ("ELITE_TEUTONIC_KNIGHT", "Elite Teutonic Knight"),
    ("VILLAGER_MALE_FARMER", "Farmer"),
    ("TREBUCHET_PACKED", "Trebuchet (packed)"),
])
def test_pretty(name, expected):
    assert units.pretty(name) == expected


# Behavior class of each Minecraft mob that an animal can use (Minecraft 1.21.1). An angry neutral mob
# (AngerTime) counts as aggressive: see docs/animals.md.
MC_CLASS = {"sheep": "passive", "cow": "passive", "pig": "passive", "chicken": "passive", "horse": "passive",
            "donkey": "passive", "camel": "passive", "rabbit": "passive", "fox": "passive", "ocelot": "passive",
            "turtle": "passive", "panda": "defensive", "polar_bear": "defensive", "llama": "defensive",
            "wolf": "defensive", "hoglin": "aggressive", "silverfish": "aggressive"}
ANIMALS_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "animals.md")


def animal_table():
    rows = [ln.split("|")[1:-1] for ln in open(ANIMALS_MD) if ln.startswith("| `")]
    return {r[0].strip(" `"): (r[1].strip(), r[3].strip(" `")) for r in rows}


def test_animals_follow_the_owner_rule():
    table = animal_table()
    mapped = {u.name: units.animal(u.name) for u in UnitInfo if units.animal(u.name)}
    assert set(table) == set(mapped), "docs/animals.md and units.ANIMALS list other animals"
    for name, (behavior, mob, tags) in mapped.items():
        assert table[name] == (behavior, mob), name
        assert str(units.classify(name)["id"]) == "minecraft:" + mob, name
        if behavior == "military":
            continue
        cls = "aggressive" if mob in ("wolf", "polar_bear") and "AngerTime" in tags else MC_CLASS[mob]
        assert cls == behavior, (name, mob)


def test_war_animals_are_not_animals():
    for name in ("BATTLE_ELEPHANT", "CAMEL_RIDER", "JAGUAR_WARRIOR", "TIGER_CAVALRY", "STANDARD_BEARER"):
        assert units.animal(name) is None, name
