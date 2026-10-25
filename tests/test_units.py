"""Every AoE2 unit and hero gives a valid Minecraft entity (or is skipped on purpose)."""
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
