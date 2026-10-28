"""Ibirapema Warrior (#2158): the Tupi barracks trains the Ibirapema Warrior from the Castle Age (slot 25: 30 food, 60
gold, 24 s) and researches Elite Ibirapema Warrior in the Imperial Age (slot 28: 1000 food, 600 gold, 60 s; the Tupi
bonus of the barracks halves the food), with the values of the AoE2 DE wiki infobox "Ibirapema Warrior" (revision
1089699). The upgrade turns the live units into elite ones, and the barracks then trains the elite one. Only the Tupi
have it."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

import units
from game import civs, combat, replay, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
UNIT = " 25:husk_spawn_egg:Ibirapema Warrior:30 food · 60 gold · 24 s · queue 0/15 "


def barracks(civ="TUPI", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["iw"] = "IBIRAPEMA_WARRIOR"
    g.game.entities.setdefault("iw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_unit_is_an_infantry_husk():
    for unit in ("IBIRAPEMA_WARRIOR", "ELITE_IBIRAPEMA_WARRIOR"):
        assert combat.INF in combat.stats(unit).classes and unit in replay.SPEEDS and len(train.HELP[unit]) <= 50
        assert units.classify(unit)["id"] == "minecraft:husk"
    assert combat.stats("ELITE_IBIRAPEMA_WARRIOR").attack > combat.stats("IBIRAPEMA_WARRIOR").attack
    assert len(train.HELP["ELITE_IBIRAPEMA_WARRIOR_UPGRADE"]) <= 50


def test_only_the_tupi_have_it():
    have = set().union(*civs.MISSING.values())
    for name in ("IBIRAPEMA_WARRIOR", "ELITE_IBIRAPEMA_WARRIOR", "ELITE_IBIRAPEMA_WARRIOR_UPGRADE"):
        assert have - set(civs.MISSING[name]) == {"TUPI"}, name


def test_the_menu_has_the_unit_from_the_castle_age_for_the_tupi():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert " 25:gray_dye:Ibirapema Warrior:30 food · 60 gold · 24 s · Needs the Castle Age" in menus(server)[-1]
    server, g = barracks(ages=CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert UNIT in menu and "Elite Ibirapema Warrior" not in menu           # the upgrade: the Imperial Age
    for civ in ("BRITONS", "MAPUCHE"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Ibirapema Warrior" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", BARRACKS, "IBIRAPEMA_WARRIOR") is None, civ


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 28:book:Elite Ibirapema Warrior:500 food · 600 gold · 60 s · research " in menus(server)[-1] + " "
    research(g, BARRACKS, "ELITE_IBIRAPEMA_WARRIOR_UPGRADE")
    assert g.soldiers["iw"] == "ELITE_IBIRAPEMA_WARRIOR"
    assert combat.stats_command("iw", "ELITE_IBIRAPEMA_WARRIOR") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 25:husk_spawn_egg:Elite Ibirapema Warrior:30 food · 60 gold · 24 s · queue 0/15 " in menu
    assert ":Ibirapema Warrior:" not in menu and "28:book" not in menu
    assert train.queue(g, "Steve", BARRACKS, "ELITE_IBIRAPEMA_WARRIOR")
    assert train.queue(g, "Steve", BARRACKS, "IBIRAPEMA_WARRIOR") is None
