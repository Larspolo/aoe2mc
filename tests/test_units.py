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


@pytest.mark.parametrize("name,reason", [("MOVEABLE_MAP_REVEALER_A", "map revealer"), ("INVISIBLE_OBJECT_C", "invisible object"),
                                         ("HINT_OBJECT", "editor hint"), ("MILITIA", None)])
def test_invisible(name, reason):
    assert units.invisible(name) == reason
    assert (units.classify(name) is None) == (reason is not None)


def test_infantry_lines_have_their_own_look():
    looks = {}
    for name, (kind, pieces, *_) in units.LINES.items():
        desc = units.classify(name)
        assert desc != units.infantry(name, units.tier_of(name, False)), name
        man = desc["Passengers"][0] if kind == "mounted" else desc
        if str(man["id"]) in ("minecraft:zombie", "minecraft:zombie_villager"):
            assert pieces[0], f"{name}: a zombie without a helmet burns in the sun"
        looks.setdefault(repr(desc), []).append(name)
    same = [v for v in looks.values() if len(v) > 1]
    assert all(v[0].removesuffix("_MALE") in n or n in v[0] for v in same for n in v), same   # only name variants


def test_each_militia_upgrade_looks_stronger():
    line = ["MILITIA", "MAN_AT_ARMS", "LONG_SWORDSMAN", "TWO_HANDED_SWORDSMAN", "CHAMPION"]
    order = [None, "leather", "chainmail", "iron", "golden", "diamond"]
    worn = [sum(order.index(p if not isinstance(p, tuple) else p[0]) for p in units.LINES[n][1]) for n in line]
    assert worn == sorted(worn) and len(set(worn)) == len(worn), worn


@pytest.mark.parametrize("name,mob", [("THE_BLACK_PRINCE", "horse"), ("PORUS", "ravager"), ("LEONIDAS", "zombie"),
                                      ("EINAR_PAUNCH_SHAKER", "skeleton"), ("HUNTING_WOLF", "wolf")])
def test_hero_base_unit(name, mob):
    assert units.classify(name, hero=True)["id"] == "minecraft:" + mob


@pytest.mark.parametrize("name", ["ELITE_HUSKARL", "ELITE_URUMI_SWORDSMAN", "ELITE_KONA", "ELITE_JARL", "ELITE_SANNAHYA"])
def test_elite_has_a_gold_trim_on_the_base_design(name):
    elite, base = units.classify(name), units.classify(name.removeprefix("ELITE_"))
    if "Passengers" in elite:
        elite, base = elite["Passengers"][0], base["Passengers"][0]
    trims = [i for i in elite["ArmorItems"] if "minecraft:trim" in i.get("components", {})]
    assert len(trims) == 1
    assert elite["HandItems"] == base["HandItems"] and elite["id"] == base["id"]


@pytest.mark.parametrize("name", sorted(n for n, _ in NAMES if units.line_unit(n)))
def test_no_empty_item_has_components(name):
    """An item without an id is invalid in Minecraft ("Tried to load invalid item")."""
    desc = units.classify(name)
    for d in [desc, *desc.get("Passengers", [])]:
        for it in [*d.get("ArmorItems", []), *d.get("HandItems", [])]:
            assert "id" in it or not len(it), (name, it)


def test_facing_map_knights_face_away_from_the_center(tmp_path):
    """tools/scenarios.py facing: knight k stands in the direction of its rotation, so it faces away from the
    center in Minecraft (#20). The owner compares this with the AoE2 editor (docs/facing.md)."""
    import math

    import aoe2mc
    import scenarios
    *_, objects, players = aoe2mc.read_scenario(scenarios.facing(str(tmp_path / "facing.aoe2scenario")))
    knights = [o for o in objects if o["name"] == "KNIGHT"]
    assert len(knights) == 8 and len([o for o in objects if o["name"] == "ARCHER"]) == 8
    for o in knights:
        yaw = math.radians(float(units.make_entity(o, players, (0, 64, 0), np.random.default_rng(0))["Rotation"][0]))
        out = np.array([o["x"] - 16.5, o["y"] - 16.5]) / 6           # from the center to the knight (x, z)
        assert np.dot([-math.sin(yaw), math.cos(yaw)], out) > 0.99    # Minecraft look direction of this yaw
