"""game/civs.py: the combat bonuses of each age of the Byzantines, Mapuche, Muisca and Jurchens (AoE2 DE wiki, #2116):
more in each age. A unit or building that exists at the age-up gets the bonus of the new age, as in AoE2."""
import pytest

from game import build, civs, combat, train

from test_civ_units import trained
from test_civ_work import setup
from test_masonry import TC
from test_tower_upgrades import setup as towers, uuid

AGES = ((), ("FEUDAL_AGE",), ("FEUDAL_AGE", "CASTLE_AGE"), ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))


def stats(civ, name, age):
    g = setup(civ)
    g.techs.update(AGES[age])
    return train.stats(g, name)


def more_in_each_age(d):
    """d: the bonus in each age. None in the Dark Age, more in each later age."""
    return d[0] == 0 and all(a < b for a, b in zip(d, d[1:]))


def test_mapuche_infantry_slingers_and_skirmishers_get_more_hit_points_in_each_age():
    for name in ("MILITIA", "SLINGER", "SKIRMISHER"):
        assert more_in_each_age([stats("MAPUCHE", name, a).hp - combat.stats(name).hp for a in range(4)]), name
    assert stats("MAPUCHE", "KNIGHT", 3).hp == combat.stats("KNIGHT").hp
    assert stats("AZTECS", "MILITIA", 3).hp == combat.stats("MILITIA").hp


def test_muisca_archers_and_the_champi_line_get_more_melee_armor_in_each_age():
    for name in ("ARCHER", "SKIRMISHER", "HAND_CANNONEER", "SLINGER"):
        assert more_in_each_age([stats("MUISCA", name, a).melee - combat.stats(name).melee for a in range(4)]), name
    assert civs.GROUPS["champi scout line, archery range units"]("CHAMPI_SCOUT", combat.stats("MILITIA"))
    for name in ("CONQUISTADOR", "MILITIA", "KNIGHT"):                  # the wiki: not the conquistador type
        assert stats("MUISCA", name, 3).melee == combat.stats(name).melee, name


def test_jurchen_mounted_units_and_fire_lancers_attack_faster_from_the_feudal_age():
    for name in ("KNIGHT", "FIRE_LANCER", "ELITE_FIRE_LANCER"):
        base = combat.stats(name).reload
        assert stats("JURCHENS", name, 0).reload == base, name
        feudal = stats("JURCHENS", name, 1).reload
        assert feudal < base and stats("JURCHENS", name, 3).reload == pytest.approx(feudal, abs=1e-3), name
    assert stats("JURCHENS", "MILITIA", 3).reload == combat.stats("MILITIA").reload


def test_byzantine_buildings_and_walls_have_more_hit_points_in_each_age():
    g = setup("BYZANTINES")
    tc = combat.stats("TOWN_CENTER").hp
    hp = [build.values(g, "TOWN_CENTER", set(t)).hp for t in AGES]
    assert tc < hp[0] and all(a < b for a, b in zip(hp, hp[1:])), hp
    assert build.values(setup("BRITONS"), "TOWN_CENTER", set(AGES[3])).hp == tc
    for age in range(4):
        assert combat.wall("STONE_WALL", age, "BYZANTINES").hp > combat.wall("STONE_WALL", age).hp
    assert combat.wall("STONE_WALL", 2, "BRITONS") == combat.wall("STONE_WALL", 2)
    assert build.values(g, "STONE_WALL", set(AGES[3])) == build.values(g, "STONE_WALL", set())   # the age: combat.wall


def test_a_unit_trained_before_the_age_up_gets_the_bonus_of_the_new_age():
    g, uuid, _ = trained("MAPUCHE", "MILITIA")
    n = len(g.game.log)
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    hp = train.stats(g, "MILITIA").hp
    assert hp > combat.stats("MILITIA").hp and f"aoe stats {uuid} {hp} " in " ".join(g.game.log[n:])


def test_a_building_of_the_map_keeps_its_lost_hit_points_and_gets_those_of_the_new_age():
    server, g = towers(age=0)
    g.data["players"]["1"]["civ"] = "BYZANTINES"
    dark, feudal = (build.values(g, "TOWN_CENTER", set(g.techs) | set(t)).hp for t in ((), ("FEUDAL_AGE",)))
    server.hp[uuid(TC)] = dark - 100                                   # the town center lost 100 hit points
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    assert feudal > dark and server.hp[uuid(TC)] == feudal - 100
    assert any(c.startswith(f"aoe building {uuid(TC)} {feudal} ") for c in server.log)
