"""War Wagon (#1889): the castle of the Koreans trains the War Wagon (200 wood, 60 gold, 21 s) and researches Elite War
Wagon in the Imperial Age (slot 5: 1000 wood, 800 gold, 75 s), with the values of the AoE2 DE wiki. The upgrade changes
the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["WAR_WAGON"]) <= 50 and "KOREANS" not in train.civs.MISSING["WAR_WAGON"]
    assert "BRITONS" in train.civs.MISSING["WAR_WAGON"]


def test_the_castle_of_the_koreans_trains_the_war_wagon():
    server, g = setup("KOREANS", food=0, wood=100, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:War Wagon:100 wood · 60 gold · 21 s · queue 0/15 " in menu
    assert "Elite War Wagon" not in menu                               # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "WAR_WAGON"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "War Wagon" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("KOREANS", food=0, wood=2000, gold=2000, ages=3)
    g.soldiers["ww"] = "WAR_WAGON"
    g.game.entities.setdefault("ww", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite War Wagon:1000 wood · 800 gold · 75 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_WAR_WAGON_UPGRADE")
    train.tick(g, 75)
    assert "ELITE_WAR_WAGON_UPGRADE" in g.techs and g.soldiers["ww"] == "ELITE_WAR_WAGON"
    assert combat.stats_command("ww", "ELITE_WAR_WAGON") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Elite War Wagon:100 wood · 60 gold · 21 s · queue 0/15 " in menu
    assert ":War Wagon:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_WAR_WAGON")
    assert train.queue(g, "Steve", CASTLE, "WAR_WAGON") is None
