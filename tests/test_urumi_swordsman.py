"""Urumi Swordsman (#1754): the castle of the Dravidians trains the urumi swordsman (65 food · 20 gold, 9 s) and
researches Elite Urumi Swordsman in the Imperial Age (slot 5: 900 food, 450 gold, 45 s), with the values of the
AoE2 DE wiki. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert combat.stats("URUMI_SWORDSMAN") and combat.stats("ELITE_URUMI_SWORDSMAN")
    assert len(train.HELP["URUMI_SWORDSMAN"]) <= 50 and "DRAVIDIANS" not in train.civs.MISSING["URUMI_SWORDSMAN"]
    assert "BRITONS" in train.civs.MISSING["URUMI_SWORDSMAN"]
    assert "DRAVIDIANS" not in train.civs.MISSING["ELITE_URUMI_SWORDSMAN_UPGRADE"]


def test_the_castle_of_the_dravidians_trains_the_urumi_swordsman():
    server, g = setup("DRAVIDIANS", food=65, wood=0, gold=20)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Urumi Swordsman:65 food · 20 gold · 9 s · queue 0/15 " in menu
    assert "Elite Urumi Swordsman" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "URUMI_SWORDSMAN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Urumi Swordsman" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("DRAVIDIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "URUMI_SWORDSMAN"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Urumi Swordsman:900 food · 450 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_URUMI_SWORDSMAN_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_URUMI_SWORDSMAN_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_URUMI_SWORDSMAN"
    assert combat.stats_command("ct", "ELITE_URUMI_SWORDSMAN") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:husk_spawn_egg:Elite Urumi Swordsman:65 food · 20 gold · 9 s · queue 0/15 " in menu
    assert ":Urumi Swordsman:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_URUMI_SWORDSMAN")
    assert train.queue(g, "Steve", CASTLE, "URUMI_SWORDSMAN") is None
