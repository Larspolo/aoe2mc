"""Hoplite (#2431): the Athenian, Spartan and Thracian barracks trains the hoplite from the Castle (Classical) Age (slot
23: 55 food, 30 gold, 28 s), and the Athenians and Spartans research Elite Hoplite (slot 24: 600 food, 550 gold, 55 s;
the Imperial Age, the Spartans one age earlier). Athenian hoplites walk 15 % faster. Values of the AoE2 wiki "Hoplite
(Chronicles)". Not here: the armor aura of a pair of hoplites."""
import pytest
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

import units
from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
UNIT = " 23:zombie_spawn_egg:Hoplite:55 food · 30 gold · 28 s · queue 0/15 "
UPGRADE = " 24:book:Elite Hoplite:600 food · 550 gold · 55 s · research "


def barracks(civ="ATHENIANS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["h"] = "HOPLITE"
    g.game.entities.setdefault("h", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def menu(civ, ages):
    server, g = barracks(civ, ages)
    train.open_menu(g, "Steve", BARRACKS)
    return menus(server)[-1] + " "


def test_the_values_are_those_of_the_wiki():
    s, e = combat.STATS["HOPLITE"], combat.STATS["ELITE_HOPLITE"]
    assert (s.hp, s.attack, s.melee, s.pierce, s.reload) == (55, 10, 1, 1, 2.0) and s.bonus == {"standard": 2}
    assert (e.hp, e.attack, e.melee, e.pierce) == (70, 12, 2, 1) and "infantry" in s.classes
    assert units.classify("HOPLITE")["id"] == units.classify("ELITE_HOPLITE")["id"] == "minecraft:zombie"
    assert all(len(train.HELP[n]) <= 50 for n in ("HOPLITE", "ELITE_HOPLITE", "ELITE_HOPLITE_UPGRADE"))


def test_the_athenians_spartans_and_thracians_have_it_and_only_two_the_elite_one():
    have = set().union(*civs.MISSING.values())
    assert have - set(civs.MISSING["HOPLITE"]) == {"ATHENIANS", "SPARTANS", "THRACIANS"}
    for name in ("ELITE_HOPLITE", "ELITE_HOPLITE_UPGRADE"):
        assert have - set(civs.MISSING[name]) == {"ATHENIANS", "SPARTANS"}, name


def test_the_menu_has_the_unit_from_the_castle_age():
    assert " 23:gray_dye:Hoplite:55 food · 30 gold · 28 s · Needs the Castle Age" in menu("ATHENIANS", ("FEUDAL_AGE",))
    m = menu("THRACIANS", IMPERIAL)
    assert UNIT in m and "Elite Hoplite" not in m
    for civ in ("BRITONS", "ACHAEMENIDS", "MACEDONIANS"):
        assert "Hoplite" not in menu(civ, CASTLE), civ


def test_the_spartans_research_the_elite_hoplite_one_age_earlier():
    assert "Elite Hoplite" not in menu("ATHENIANS", CASTLE)                 # the upgrade: the Imperial Age
    assert UPGRADE in menu("SPARTANS", CASTLE)
    assert UPGRADE in menu("ATHENIANS", IMPERIAL)


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks("SPARTANS", CASTLE)
    research(g, BARRACKS, "ELITE_HOPLITE_UPGRADE")
    assert g.soldiers["h"] == "ELITE_HOPLITE"
    assert combat.stats_command("h", "ELITE_HOPLITE") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    m = menus(server)[-1] + " "
    assert " 23:zombie_spawn_egg:Elite Hoplite:55 food · 30 gold · 25 s · queue 0/15 " in m and ":Hoplite:" not in m
    assert train.queue(g, "Steve", BARRACKS, "ELITE_HOPLITE")


@pytest.mark.parametrize("unit", ["HOPLITE", "ELITE_HOPLITE"])
def test_an_athenian_hoplite_walks_15_percent_faster(unit):
    _, athenian = barracks("ATHENIANS")
    _, spartan = barracks("SPARTANS")
    assert train.speed(athenian, unit) == pytest.approx(1.15 * train.speed(spartan, unit))
    assert train.speed(athenian, "MILITIA") == train.speed(spartan, "MILITIA")
