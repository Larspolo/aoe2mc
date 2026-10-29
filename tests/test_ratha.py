"""Ratha (#1891): the castle of the Bengalis trains the ratha and researches Elite Ratha in the Imperial Age. The ratha
stays in its ranged mode (the mode switch is not in the game program). The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_bengalis_trains_the_ratha():
    server, g = setup("BENGALIS", food=2000, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Ratha").endswith(" · queue 0/15")
    assert item(menu, "Elite Ratha") is None                           # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, int(item(menu, "Ratha").split(":")[0])) == 1
    assert g.queues[rect][0]["name"] == "RATHA"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ratha" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BENGALIS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["r"] = "RATHA"
    g.game.entities.setdefault("r", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Elite Ratha").endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATHA_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_RATHA_UPGRADE", "CASTLE"))
    assert "ELITE_RATHA_UPGRADE" in g.techs and g.soldiers["r"] == "ELITE_RATHA"
    assert combat.stats_command("r", "ELITE_RATHA", train.stats(g, "ELITE_RATHA")) in server.log   # Bengali cavalry (#2249)
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Ratha").endswith(" · queue 0/15")
    assert item(menu, "Ratha") is None                       # only the elite unit
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATHA")
    assert train.queue(g, "Steve", CASTLE, "RATHA") is None
