"""Temple Guard (#2157): the Muisca barracks trains the temple guard from the Castle Age (slot 23: 70 food, 45 gold,
28 s) and researches Elite Temple Guard in the Imperial Age (slot 24: 500 food, 650 gold, 60 s), with the values of the
AoE2 DE wiki infobox "Temple Guard" (revision 1090786). The upgrade turns the live guards into elite ones, and the
barracks then trains the elite one (24 s). Only the Muisca have it. Not here: the monastery as a second building, and
the faster attacks in a long fight."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

import units
from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
UNIT = " 23:husk_spawn_egg:Temple Guard:70 food · 45 gold · 28 s · queue 0/15 "


def barracks(civ="MUISCA", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["tg"] = "TEMPLE_GUARD"
    g.game.entities.setdefault("tg", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_the_wiki():
    for unit in ("TEMPLE_GUARD", "ELITE_TEMPLE_GUARD"):
        assert len(train.HELP[unit]) <= 50
        assert units.classify(unit)["id"] == "minecraft:husk"
    assert len(train.HELP["ELITE_TEMPLE_GUARD_UPGRADE"]) <= 50


def test_only_the_muisca_have_it():
    have = set().union(*civs.MISSING.values())
    for name in ("TEMPLE_GUARD", "ELITE_TEMPLE_GUARD", "ELITE_TEMPLE_GUARD_UPGRADE"):
        assert have - set(civs.MISSING[name]) == {"MUISCA"}, name


def test_the_menu_has_the_unit_from_the_castle_age_for_the_muisca():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert " 23:gray_dye:Temple Guard:70 food · 45 gold · 28 s · Needs the Castle Age" in menus(server)[-1]
    server, g = barracks(ages=CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert UNIT in menu and "Elite Temple Guard" not in menu                 # the upgrade: the Imperial Age
    for civ in ("BRITONS", "AZTECS"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Temple Guard" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", BARRACKS, "TEMPLE_GUARD") is None, civ


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 24:book:Elite Temple Guard:500 food · 650 gold · 60 s · research " in menus(server)[-1] + " "
    research(g, BARRACKS, "ELITE_TEMPLE_GUARD_UPGRADE")
    assert g.soldiers["tg"] == "ELITE_TEMPLE_GUARD"
    assert combat.stats_command("tg", "ELITE_TEMPLE_GUARD") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 23:husk_spawn_egg:Elite Temple Guard:70 food · 45 gold · 24 s · queue 0/15 " in menu
    assert ":Temple Guard:" not in menu and "24:book" not in menu
    assert train.queue(g, "Steve", BARRACKS, "ELITE_TEMPLE_GUARD")
    assert train.queue(g, "Steve", BARRACKS, "TEMPLE_GUARD") is None
