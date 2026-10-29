"""Halberdier (#1499): the barracks researches the upgrade in the Imperial Age, after Pikeman, in its slot (the UpCost
and UpTime of the AoE2 DE wiki infobox "Pikeman"). Then the live pikemen are halberdiers and the barracks trains the
halberdier."""
from menu_line import item
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train


def test_the_upgrade_is_in_the_slot_of_pikeman_in_the_imperial_age_after_pikeman():
    server, g = setup()
    research(g, BARRACKS, "PIKEMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Halberdier" not in menus(server)[-1]                       # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", BARRACKS)
    assert item(menus(server)[-1], "Halberdier").endswith(" · research")
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    train.open_menu(g, "Steve", BARRACKS)
    assert "Halberdier" not in menus(server)[-1]                       # not before Pikeman


def test_the_live_pikemen_become_halberdiers_and_the_barracks_trains_them():
    server, g = setup(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    research(g, BARRACKS, "PIKEMAN_UPGRADE")
    assert g.soldiers["p"] == "PIKEMAN"
    research(g, BARRACKS, "HALBERDIER_UPGRADE")
    assert g.soldiers["p"] == "HALBERDIER"
    assert combat.stats_command("p", "HALBERDIER") in server.log and combat.label_command("p", "HALBERDIER") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert item(menu, "Halberdier").endswith(" · queue 0/15") and item(menu, "Pikeman") is None
    assert train.queue(g, "Steve", BARRACKS, "HALBERDIER") and train.queue(g, "Steve", BARRACKS, "PIKEMAN") is None
