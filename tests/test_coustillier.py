"""Coustillier (#1753): the castle of the Burgundians trains the Coustillier and researches Elite Coustillier in the
Imperial Age. The upgrade changes the live and the new units."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_help_texts_are_short():
    for name in ("COUSTILLIER", "ELITE_COUSTILLIER", "ELITE_COUSTILLIER_UPGRADE"):
        assert len(train.HELP[name]) <= 50


def test_the_castle_of_the_malay_trains_the_coustillier_warrior():
    server, g = setup("BURGUNDIANS", food=10000, wood=0, gold=10000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "COUSTILLIER") + "queue 0/15 " in menu
    assert "Elite Coustillier" not in menu                        # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(entry(g, CASTLE, "COUSTILLIER").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "COUSTILLIER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Karambit" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BURGUNDIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["co"] = "COUSTILLIER"
    g.game.entities.setdefault("co", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " " + entry(g, CASTLE, "ELITE_COUSTILLIER_UPGRADE") + "research " in menus(server)[-1] + " "
    slot = entry(g, CASTLE, "ELITE_COUSTILLIER_UPGRADE").split(":")[0]
    assert train.queue(g, "Steve", CASTLE, "ELITE_COUSTILLIER_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_COUSTILLIER_UPGRADE"])
    assert "ELITE_COUSTILLIER_UPGRADE" in g.techs and g.soldiers["co"] == "ELITE_COUSTILLIER"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "ELITE_COUSTILLIER") + "queue 0/15 " in menu
    assert ":Coustillier:" not in menu and f" {slot}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_COUSTILLIER")
    assert train.queue(g, "Steve", CASTLE, "COUSTILLIER") is None
