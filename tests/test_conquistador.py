"""Conquistador (#1744): the castle of the Spanish trains the Conquistador and researches Elite Conquistador in the
Imperial Age. The upgrade changes the live and the new units."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_help_text_is_short():
    assert len(train.HELP["CONQUISTADOR"]) <= 50


def test_the_castle_of_the_spanish_trains_the_conquistador():
    server, g = setup("SPANISH", food=10000, wood=10000, gold=10000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "CONQUISTADOR") + "queue 0/15 " in menu
    assert "Elite Conquistador" not in menu                            # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(entry(g, CASTLE, "CONQUISTADOR").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "CONQUISTADOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Conquistador" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("SPANISH", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["cq"] = "CONQUISTADOR"
    g.game.entities.setdefault("cq", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " " + entry(g, CASTLE, "ELITE_CONQUISTADOR_UPGRADE") + "research " in menus(server)[-1] + " "
    slot = entry(g, CASTLE, "ELITE_CONQUISTADOR_UPGRADE").split(":")[0]
    assert train.queue(g, "Steve", CASTLE, "ELITE_CONQUISTADOR_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_CONQUISTADOR_UPGRADE"])
    assert "ELITE_CONQUISTADOR_UPGRADE" in g.techs and g.soldiers["cq"] == "ELITE_CONQUISTADOR"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "ELITE_CONQUISTADOR") + "queue 0/15 " in menu
    assert ":Conquistador:" not in menu and f" {slot}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CONQUISTADOR")
    assert train.queue(g, "Steve", CASTLE, "CONQUISTADOR") is None
