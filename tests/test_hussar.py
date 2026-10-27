"""Hussar (#1502): the stable researches the upgrade in the Imperial Age, after Light Cavalry and in its slot (500 food,
600 gold, 50 s: the UpCost and UpTime of the AoE2 DE wiki infobox "Light Cavalry"). Then the live light cavalry are
hussars and the stable trains the hussar (80 food, 30 s). The civilizations without it in the wiki chart do not see it."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["HUSSAR_UPGRADE"] == {"food": 500, "gold": 600} and train.TRAIN_TIMES["HUSSAR_UPGRADE"] == 50
    assert train.TECH_AGE["HUSSAR_UPGRADE"] == 3 and train.AFTER["HUSSAR_UPGRADE"] == "LIGHT_CAVALRY_UPGRADE"
    assert train.COSTS["HUSSAR"] == {"food": 80} and train.TRAIN_TIMES["HUSSAR"] == 30
    assert combat.stats("HUSSAR").hp == 75 and combat.sight("HUSSAR") == 10 and len(train.HELP["HUSSAR_UPGRADE"]) <= 50
    assert {"BRITONS", "FRANKS", "POLES", "TEUTONS"} <= set(civs.MISSING["HUSSAR_UPGRADE"])
    assert not {"HUNS", "MAGYARS", "WU"} & set(civs.MISSING["HUSSAR_UPGRADE"])


def test_the_upgrade_is_in_the_slot_of_light_cavalry_in_the_imperial_age():
    server, g = setup()
    research(g, STABLE, "LIGHT_CAVALRY_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    assert "Hussar" not in menus(server)[-1]                           # the Castle Age
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", STABLE)
    assert " 2:book:Hussar:500 food · 600 gold · 50 s · research " in menus(server)[-1] + " "
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
    assert "0:horse_spawn_egg:Hussar:80 food · 30 s · queue" in menu and ":Light Cavalry:" not in menu
    assert train.queue(g, "Steve", STABLE, "HUSSAR") and train.queue(g, "Steve", STABLE, "LIGHT_CAVALRY") is None
