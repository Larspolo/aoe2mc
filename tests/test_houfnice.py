"""Houfnice (#2143): the siege workshop of the Bohemians researches Houfnice in the Imperial Age (AoE2 DE wiki "Unique
upgrade"), and their bombard cannons become houfnices (wiki infobox "Houfnice"). Other civilizations do not see it."""
from menu_line import item
from test_forging import menus
from test_siege_upgrades import WORKSHOP, research, setup

from game import combat, train


def workshop(civ="BOHEMIANS"):
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.add("CHEMISTRY")
    g.soldiers["b"] = "BOMBARD_CANNON"
    g.game.entities.setdefault("b", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_only_the_bohemians_see_the_upgrade():
    server, g = workshop("FRANKS")
    train.open_menu(g, "Steve", WORKSHOP)
    assert "Houfnice" not in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "HOUFNICE_UPGRADE") is None


def test_the_upgrade_changes_the_live_and_the_new_bombard_cannons():
    server, g = workshop()
    train.open_menu(g, "Steve", WORKSHOP)
    assert item(menus(server)[-1], "Houfnice").endswith(" · research")
    research(g, WORKSHOP, "HOUFNICE_UPGRADE")
    assert g.soldiers["b"] == "HOUFNICE"
    assert combat.stats_command("b", "HOUFNICE", train.stats(g, "HOUFNICE")) in server.log
    train.open_menu(g, "Steve", WORKSHOP)
    menu = menus(server)[-1]
    assert item(menu, "Houfnice").endswith(" · queue 0/15")                 # the unit, not the research
    assert "Bombard Cannon" not in menu
    assert train.queue(g, "Steve", WORKSHOP, "HOUFNICE")


def test_no_upgrade_before_the_imperial_age():
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    g.data["players"] = {"1": {"civ": "BOHEMIANS"}}
    train.open_menu(g, "Steve", WORKSHOP)
    assert ":book:Houfnice:" not in menus(server)[-1]
    assert train.queue(g, "Steve", WORKSHOP, "HOUFNICE_UPGRADE") is None
