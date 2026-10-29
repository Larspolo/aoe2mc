"""Legionary (#2015): the Romans upgrade the long swordsman to the legionary at the barracks in the Imperial Age, in
place of the Two-Handed Swordsman and Champion upgrades and in the slot of Long Swordsman (the AoE2 DE wiki "Legionary
(Age of Empires II)", "Comparison with similar units"). Then the live long swordsmen are legionaries and the barracks
trains the legionary. The other civilizations do not see it."""
from menu_line import item
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def imperial(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    research(g, BARRACKS, "LONG_SWORDSMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    return server, g


def test_the_romans_see_it_in_place_of_two_handed_swordsman():
    server, _ = imperial("ROMANS")
    menu = menus(server)[-1]
    assert item(menu, "Legionary").endswith(" · research")
    assert ":Two-Handed Swordsman:" not in menu


def test_other_civs_see_the_two_handed_swordsman_only():
    server, _ = imperial("FRANKS")
    menu = menus(server)[-1]
    assert "Legionary" not in menu and item(menu, "Two-Handed Swordsman").split(":")[1] == "book"
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": "ROMANS"}}
    train.open_menu(g, "Steve", BARRACKS)
    assert "Legionary" not in menus(server)[-1]                         # not before Long Swordsman


def test_the_romans_have_no_champion_after_it():
    server, g = imperial("ROMANS")
    research(g, BARRACKS, "LEGIONARY_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert ":Champion:" not in menus(server)[-1]


def test_the_live_long_swordsmen_become_legionaries_and_the_barracks_trains_them():
    server, g = imperial("ROMANS")
    assert g.soldiers["a"] == "LONG_SWORDSMAN"
    research(g, BARRACKS, "LEGIONARY_UPGRADE")
    assert g.soldiers["a"] == "LEGIONARY"
    assert combat.stats_command("a", "LEGIONARY") in server.log
    assert combat.label_command("a", "LEGIONARY") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert item(menu, "Legionary").endswith(" · queue 0/15") and item(menu, "Long Swordsman") is None
    assert train.queue(g, "Steve", BARRACKS, "LEGIONARY")
    assert train.queue(g, "Steve", BARRACKS, "LONG_SWORDSMAN") is None
