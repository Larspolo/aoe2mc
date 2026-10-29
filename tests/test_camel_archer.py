"""Camel Archer (#1723): the castle of the Berbers trains the camel archer and researches Elite Camel Archer in the
Imperial Age. The upgrade changes the live and the new units."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_help_texts_are_short():
    for name in ("CAMEL_ARCHER", "ELITE_CAMEL_ARCHER", "ELITE_CAMEL_ARCHER_UPGRADE"):
        assert len(train.HELP[name]) <= 50


def test_the_castle_of_the_berbers_trains_the_camel_archer():
    server, g = setup("BERBERS", wood=10000, gold=10000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "CAMEL_ARCHER") + "queue 0/15 " in menu
    assert "Elite Camel" not in menu                                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(entry(g, CASTLE, "CAMEL_ARCHER").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "CAMEL_ARCHER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Camel" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BERBERS", wood=2000, gold=2000, ages=3)
    g.soldiers["ca"] = "CAMEL_ARCHER"
    g.game.entities.setdefault("ca", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " " + entry(g, CASTLE, "ELITE_CAMEL_ARCHER_UPGRADE") + "research " in menus(server)[-1] + " "
    slot = entry(g, CASTLE, "ELITE_CAMEL_ARCHER_UPGRADE").split(":")[0]
    assert train.queue(g, "Steve", CASTLE, "ELITE_CAMEL_ARCHER_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_CAMEL_ARCHER_UPGRADE"])
    assert "ELITE_CAMEL_ARCHER_UPGRADE" in g.techs and g.soldiers["ca"] == "ELITE_CAMEL_ARCHER"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "ELITE_CAMEL_ARCHER") + "queue 0/15 " in menu
    assert ":Camel Archer:" not in menu and f" {slot}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CAMEL_ARCHER")
    assert train.queue(g, "Steve", CASTLE, "CAMEL_ARCHER") is None
