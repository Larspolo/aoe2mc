"""Chakram Thrower (#1624): the castle of the Gurjaras trains the chakram thrower (65 food, 30 gold, 15 s) and
researches Elite Chakram Thrower in the Imperial Age (slot 5: 1000 food, 650 gold, 45 s), with the values of the AoE2 DE
wiki infobox "Chakram Thrower (Age of Empires II)". The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert {"CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER"} <= combat.MELEE_RANGED
    for name in ("CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "GURJARAS" not in train.civs.MISSING[name] and "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_gurjaras_trains_the_chakram_thrower():
    server, g = setup("GURJARAS", food=65, wood=0, gold=30)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:drowned_spawn_egg:Chakram Thrower:65 food · 30 gold · 15 s · queue 0/15 " in menu
    assert "Elite Chakram" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "CHAKRAM_THROWER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Chakram" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("GURJARAS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "CHAKRAM_THROWER"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Chakram Thrower:1000 food · 650 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_CHAKRAM_THROWER_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_CHAKRAM_THROWER_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_CHAKRAM_THROWER"
    assert combat.stats_command("ct", "ELITE_CHAKRAM_THROWER") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:drowned_spawn_egg:Elite Chakram Thrower:65 food · 30 gold · 15 s · queue 0/15 " in menu
    assert ":Chakram Thrower:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CHAKRAM_THROWER")
    assert train.queue(g, "Steve", CASTLE, "CHAKRAM_THROWER") is None
