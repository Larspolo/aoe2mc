"""Rattan Archer (#1888): the castle of the Vietnamese trains the rattan archer (50 wood, 45 gold, 16 s) and researches
Elite Rattan Archer in the Imperial Age (slot 5: 800 food, 750 gold, 45 s), with the values of the AoE2 DE wiki "Rattan
Archer". The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["RATTAN_ARCHER"]) <= 50 and "VIETNAMESE" not in train.civs.MISSING["RATTAN_ARCHER"]
    assert "BRITONS" in train.civs.MISSING["RATTAN_ARCHER"]
    assert "VIETNAMESE" not in train.civs.MISSING["ELITE_RATTAN_ARCHER_UPGRADE"]


def test_the_castle_of_the_vietnamese_trains_the_rattan_archer():
    server, g = setup("VIETNAMESE", wood=50, gold=45)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Rattan Archer:50 wood · 45 gold · 16 s · queue 0/15 " in menu
    assert "Elite Rattan Archer" not in menu                           # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "RATTAN_ARCHER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Rattan Archer" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("VIETNAMESE", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["ct"] = "RATTAN_ARCHER"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Rattan Archer:800 food · 750 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATTAN_ARCHER_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_RATTAN_ARCHER_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_RATTAN_ARCHER"
    assert combat.stats_command("ct", "ELITE_RATTAN_ARCHER", train.stats(g, "ELITE_RATTAN_ARCHER")) in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Elite Rattan Archer:50 wood · 45 gold · 16 s · queue 0/15 " in menu
    assert ":Rattan Archer:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATTAN_ARCHER")
    assert train.queue(g, "Steve", CASTLE, "RATTAN_ARCHER") is None
