"""Halberdier (#1499): the barracks researches the upgrade in the Imperial Age, after Pikeman, in its slot (300 food,
600 gold, 50 s: the UpCost and UpTime of the AoE2 DE wiki infobox "Pikeman"). Then the live pikemen are halberdiers
and the barracks trains the halberdier (35 food, 25 wood, 22 s)."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train


def test_the_values_are_those_of_aoe2():
    assert train.TECH_AGE["HALBERDIER_UPGRADE"] == 3 and train.AFTER["HALBERDIER_UPGRADE"] == "PIKEMAN_UPGRADE"
    assert combat.stats("HALBERDIER").hp == 60 and len(train.HELP["HALBERDIER_UPGRADE"]) <= 50


def test_the_upgrade_is_in_the_slot_of_pikeman_in_the_imperial_age_after_pikeman():
    server, g = setup()
    research(g, BARRACKS, "PIKEMAN_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Halberdier" not in menus(server)[-1]                       # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", BARRACKS)
    assert " 3:book:Halberdier:300 food · 600 gold · 50 s · research " in menus(server)[-1] + " "
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
    assert "1:zombie_spawn_egg:Halberdier:35 food · 25 wood · 22 s · queue" in menu and ":Pikeman:" not in menu
    assert train.queue(g, "Steve", BARRACKS, "HALBERDIER") and train.queue(g, "Steve", BARRACKS, "PIKEMAN") is None
