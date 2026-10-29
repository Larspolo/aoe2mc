"""Chakram Thrower (#1624): the castle of the Gurjaras trains the chakram thrower and researches Elite Chakram Thrower
in the Imperial Age. The upgrade changes the live and the new units."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_help_texts_are_short():
    for name in ("CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER", "ELITE_CHAKRAM_THROWER_UPGRADE"):
        assert len(train.HELP[name]) <= 50


def test_the_castle_of_the_gurjaras_trains_the_chakram_thrower():
    server, g = setup("GURJARAS", food=10000, wood=0, gold=10000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "CHAKRAM_THROWER") + "queue 0/15 " in menu
    assert "Elite Chakram" not in menu                                 # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(entry(g, CASTLE, "CHAKRAM_THROWER").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "CHAKRAM_THROWER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Chakram" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("GURJARAS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "CHAKRAM_THROWER"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " " + entry(g, CASTLE, "ELITE_CHAKRAM_THROWER_UPGRADE") + "research " in menus(server)[-1] + " "
    slot = entry(g, CASTLE, "ELITE_CHAKRAM_THROWER_UPGRADE").split(":")[0]
    assert train.queue(g, "Steve", CASTLE, "ELITE_CHAKRAM_THROWER_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_CHAKRAM_THROWER_UPGRADE"])
    assert "ELITE_CHAKRAM_THROWER_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_CHAKRAM_THROWER"
    assert combat.stats_command("ct", "ELITE_CHAKRAM_THROWER") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "ELITE_CHAKRAM_THROWER") + "queue 0/15 " in menu
    assert ":Chakram Thrower:" not in menu and f" {slot}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CHAKRAM_THROWER")
    assert train.queue(g, "Steve", CASTLE, "CHAKRAM_THROWER") is None
