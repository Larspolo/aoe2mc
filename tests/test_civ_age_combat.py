"""game/civs.py: the combat bonuses of each age of the Byzantines, Mapuche, Muisca and Jurchens (AoE2 DE wiki, #2116).
A unit or building that exists at the age-up gets the bonus of the new age, as in AoE2."""
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


def test_mapuche_infantry_slingers_and_skirmishers_get_5_10_15_hit_points():
    for name in ("MILITIA", "SLINGER", "SKIRMISHER"):
        assert [stats("MAPUCHE", name, a).hp - combat.stats(name).hp for a in range(4)] == [0, 5, 10, 15], name
    assert stats("MAPUCHE", "KNIGHT", 3).hp == combat.stats("KNIGHT").hp
    assert stats("AZTECS", "MILITIA", 3).hp == combat.stats("MILITIA").hp


def test_muisca_archers_and_the_champi_line_get_1_2_3_melee_armor():
    for name in ("ARCHER", "SKIRMISHER", "HAND_CANNONEER", "SLINGER"):
        assert [stats("MUISCA", name, a).melee - combat.stats(name).melee for a in range(4)] == [0, 1, 2, 3], name
    assert civs.GROUPS["champi scout line, archery range units"]("CHAMPI_SCOUT", combat.stats("MILITIA"))
    for name in ("CONQUISTADOR", "MILITIA", "KNIGHT"):                  # the wiki: not the conquistador type
        assert stats("MUISCA", name, 3).melee == combat.stats(name).melee, name


def test_jurchen_mounted_units_and_fire_lancers_attack_25_percent_faster_from_the_feudal_age():
    for name in ("KNIGHT", "FIRE_LANCER", "ELITE_FIRE_LANCER"):
        base = combat.stats(name).reload
        assert stats("JURCHENS", name, 0).reload == base, name
        assert [stats("JURCHENS", name, a).reload for a in (1, 3)] == [pytest.approx(base / 1.25, abs=1e-3)] * 2, name
    assert stats("JURCHENS", "MILITIA", 3).reload == combat.stats("MILITIA").reload


def test_byzantine_buildings_and_walls_have_10_20_30_40_percent_more_hit_points():
    g = setup("BYZANTINES")
    tc = combat.stats("TOWN_CENTER").hp
    assert [build.values(g, "TOWN_CENTER", set(t)).hp for t in AGES] == [round(tc * f) for f in (1.1, 1.2, 1.3, 1.4)]
    assert build.values(setup("BRITONS"), "TOWN_CENTER", set(AGES[3])).hp == tc
    for age, f in enumerate((1.1, 1.2, 1.3, 1.4)):
        assert combat.wall("STONE_WALL", age, "BYZANTINES").hp == round(combat.wall("STONE_WALL", age).hp * f)
    assert combat.wall("STONE_WALL", 2, "BRITONS") == combat.wall("STONE_WALL", 2)
    assert build.values(g, "STONE_WALL", set(AGES[3])) == build.values(g, "STONE_WALL", set())   # the age: combat.wall


def test_a_unit_trained_before_the_age_up_gets_the_bonus_of_the_new_age():
    g, uuid, _ = trained("MAPUCHE", "MILITIA")
    n = len(g.game.log)
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    assert f"aoe stats {uuid} {combat.stats('MILITIA').hp + 5} " in " ".join(g.game.log[n:])


def test_a_building_of_the_map_keeps_its_lost_hit_points_and_gets_those_of_the_new_age():
    server, g = towers(age=0)
    g.data["players"]["1"]["civ"] = "BYZANTINES"
    tc = combat.stats("TOWN_CENTER").hp
    server.hp[uuid(TC)] = round(tc * 1.1) - 100                     # the town center lost 100 hit points
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    assert server.hp[uuid(TC)] == round(tc * 1.2) - 100
    assert any(c.startswith(f"aoe building {uuid(TC)} {round(tc * 1.2)} ") for c in server.log)
