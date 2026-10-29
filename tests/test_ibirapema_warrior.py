"""Ibirapema Warrior (#2158): the Tupi barracks trains the Ibirapema Warrior from the Castle Age and researches Elite
Ibirapema Warrior in the Imperial Age, with the values of the AoE2 DE wiki infobox "Ibirapema Warrior" (revision
1089699). The upgrade turns the live units into elite ones, and the barracks then trains the elite one. Only the Tupi
have it."""
from menu_line import item
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def barracks(civ="TUPI", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["iw"] = "IBIRAPEMA_WARRIOR"
    g.game.entities.setdefault("iw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_menu_has_the_unit_from_the_castle_age_for_the_tupi():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert item(menus(server)[-1], "Ibirapema Warrior").endswith(" · Needs the Castle Age")
    server, g = barracks(ages=CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert item(menu, "Ibirapema Warrior").endswith(" · queue 0/15") and "Elite Ibirapema Warrior" not in menu           # the upgrade: the Imperial Age
    for civ in ("BRITONS", "MAPUCHE"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Ibirapema Warrior" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", BARRACKS, "IBIRAPEMA_WARRIOR") is None, civ


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert item(menus(server)[-1], "Elite Ibirapema Warrior").endswith(" · research")
    research(g, BARRACKS, "ELITE_IBIRAPEMA_WARRIOR_UPGRADE")
    assert g.soldiers["iw"] == "ELITE_IBIRAPEMA_WARRIOR"
    assert combat.stats_command("iw", "ELITE_IBIRAPEMA_WARRIOR") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert item(menu, "Elite Ibirapema Warrior").endswith(" · queue 0/15")
    assert item(menu, "Ibirapema Warrior") is None                     # only the elite unit
    assert train.queue(g, "Steve", BARRACKS, "ELITE_IBIRAPEMA_WARRIOR")
    assert train.queue(g, "Steve", BARRACKS, "IBIRAPEMA_WARRIOR") is None
