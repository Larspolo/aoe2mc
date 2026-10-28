"""Ghulam (#1756): the castle of the Hindustanis trains the ghulam (30 food, 45 gold, 12 s) and researches Elite Ghulam
in the Imperial Age (slot 5: 950 food, 575 gold, 45 s), with the values of the AoE2 DE wiki infobox "Ghulam (Age of
Empires II)". The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert "HINDUSTANIS" not in train.civs.MISSING["GHULAM"] and "BRITONS" in train.civs.MISSING["GHULAM"]


def test_the_castle_of_the_hindustanis_trains_the_ghulam():
    server, g = setup("HINDUSTANIS", food=30, wood=0, gold=45)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Ghulam:30 food · 45 gold · 12 s · queue 0/15 " in menu
    assert "Elite Ghulam" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "GHULAM"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ghulam" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("HINDUSTANIS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["gh"] = "GHULAM"
    g.game.entities.setdefault("gh", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Ghulam:950 food · 575 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_GHULAM_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_GHULAM_UPGRADE" in g.techs and g.soldiers["gh"] == "ELITE_GHULAM"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Elite Ghulam:30 food · 45 gold · 12 s · queue 0/15 " in menu
    assert ":Ghulam:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_GHULAM")
    assert train.queue(g, "Steve", CASTLE, "GHULAM") is None
