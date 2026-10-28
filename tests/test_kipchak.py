"""Kipchak (#1885): the castle of the Cumans trains the Kipchak (60 wood, 35 gold, 20 s) and researches Elite Kipchak
in the Imperial Age (slot 5: 1100 food, 1000 wood, 65 s), with the values of the AoE2 DE wiki. The upgrade changes the
live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["KIPCHAK"]) <= 50 and "CUMANS" not in train.civs.MISSING["KIPCHAK"]
    assert "BRITONS" in train.civs.MISSING["KIPCHAK"]


def test_the_castle_of_the_cumans_trains_the_kipchak():
    server, g = setup("CUMANS", food=0, wood=60, gold=35)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_horse_spawn_egg:Kipchak:60 wood · 35 gold · 20 s · queue 0/15 " in menu
    assert "Elite Kipchak" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "KIPCHAK"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Kipchak" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("CUMANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["kc"] = "KIPCHAK"
    g.game.entities.setdefault("kc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Kipchak:1100 food · 1000 wood · 65 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_KIPCHAK_UPGRADE")
    train.tick(g, 65)
    assert "ELITE_KIPCHAK_UPGRADE" in g.techs and g.soldiers["kc"] == "ELITE_KIPCHAK"
    assert combat.stats_command("kc", "ELITE_KIPCHAK") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_horse_spawn_egg:Elite Kipchak:60 wood · 35 gold · 20 s · queue 0/15 " in menu
    assert ":Kipchak:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_KIPCHAK")
    assert train.queue(g, "Steve", CASTLE, "KIPCHAK") is None
