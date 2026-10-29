"""Centurion (#1749): the castle of the Romans trains the Centurion and researches Elite Centurion in the Imperial Age.
The upgrade changes the live and the new units."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_help_texts_are_short():
    for name in ("CENTURION", "ELITE_CENTURION", "ELITE_CENTURION_UPGRADE"):
        assert len(train.HELP[name]) <= 50


def test_the_castle_of_the_romans_trains_the_centurion():
    server, g = setup("ROMANS", food=10000, wood=0, gold=10000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "CENTURION") + "queue 0/15 " in menu
    assert "Elite Centurion" not in menu                               # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(entry(g, CASTLE, "CENTURION").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "CENTURION"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Centurion" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ROMANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ce"] = "CENTURION"
    g.game.entities.setdefault("ce", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " " + entry(g, CASTLE, "ELITE_CENTURION_UPGRADE") + "research " in menus(server)[-1] + " "
    slot = entry(g, CASTLE, "ELITE_CENTURION_UPGRADE").split(":")[0]
    assert train.queue(g, "Steve", CASTLE, "ELITE_CENTURION_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_CENTURION_UPGRADE"])
    assert "ELITE_CENTURION_UPGRADE" in g.techs and g.soldiers["ce"] == "ELITE_CENTURION"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "ELITE_CENTURION") + "queue 0/15 " in menu
    assert ":Centurion:" not in menu and f" {slot}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CENTURION")
    assert train.queue(g, "Steve", CASTLE, "CENTURION") is None
