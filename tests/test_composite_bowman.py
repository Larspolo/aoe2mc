"""Composite Bowman (#1759): the castle of the Armenians trains the Composite Bowman and researches Elite Composite
Bowman in the Imperial Age. The upgrade changes the live and the new units."""
from test_castle_upgrades import entry
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_help_text_is_short():
    assert len(train.HELP["COMPOSITE_BOWMAN"]) <= 50


def test_the_castle_of_the_armenians_trains_the_composite_bowman():
    server, g = setup("ARMENIANS", food=10000, wood=10000, gold=10000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "COMPOSITE_BOWMAN") + "queue 0/15 " in menu
    assert "Elite Composite" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(entry(g, CASTLE, "COMPOSITE_BOWMAN").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "COMPOSITE_BOWMAN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Composite" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ARMENIANS", food=0, wood=2000, gold=2000, ages=3)
    g.soldiers["cb"] = "COMPOSITE_BOWMAN"
    g.game.entities.setdefault("cb", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " " + entry(g, CASTLE, "ELITE_COMPOSITE_BOWMAN_UPGRADE") + "research " in menus(server)[-1] + " "
    slot = entry(g, CASTLE, "ELITE_COMPOSITE_BOWMAN_UPGRADE").split(":")[0]
    assert train.queue(g, "Steve", CASTLE, "ELITE_COMPOSITE_BOWMAN_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_COMPOSITE_BOWMAN_UPGRADE"])
    assert "ELITE_COMPOSITE_BOWMAN_UPGRADE" in g.techs and g.soldiers["cb"] == "ELITE_COMPOSITE_BOWMAN"
    assert combat.stats_command("cb", "ELITE_COMPOSITE_BOWMAN") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " " + entry(g, CASTLE, "ELITE_COMPOSITE_BOWMAN") + "queue 0/15 " in menu
    assert ":Composite Bowman:" not in menu and f" {slot}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_COMPOSITE_BOWMAN")
    assert train.queue(g, "Steve", CASTLE, "COMPOSITE_BOWMAN") is None
