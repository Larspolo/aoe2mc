"""Hussar (#1502): the stable researches the upgrade in the Imperial Age, after Light Cavalry and in its slot (the
UpCost and UpTime of the AoE2 DE wiki infobox "Light Cavalry"). Then the live light cavalry are hussars and the stable
trains the hussar."""
from menu_line import item
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import combat, train


def test_the_upgrade_is_in_the_slot_of_light_cavalry_in_the_imperial_age():
    server, g = setup()
    research(g, STABLE, "LIGHT_CAVALRY_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    assert "Hussar" not in menus(server)[-1]                           # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", STABLE)
    assert item(menus(server)[-1], "Hussar").endswith(" · research")
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    train.open_menu(g, "Steve", STABLE)
    assert "Hussar" not in menus(server)[-1]                           # not before Light Cavalry


def test_the_live_light_cavalry_become_hussars_and_the_stable_trains_them():
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    research(g, STABLE, "LIGHT_CAVALRY_UPGRADE")
    assert g.soldiers["l"] == "LIGHT_CAVALRY"
    research(g, STABLE, "HUSSAR_UPGRADE")
    assert g.soldiers["l"] == "HUSSAR"
    assert combat.stats_command("l", "HUSSAR") in server.log and combat.label_command("l", "HUSSAR") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert item(menu, "Hussar").endswith(" · queue 0/15") and item(menu, "Light Cavalry") is None
    assert train.queue(g, "Steve", STABLE, "HUSSAR") and train.queue(g, "Steve", STABLE, "LIGHT_CAVALRY") is None
