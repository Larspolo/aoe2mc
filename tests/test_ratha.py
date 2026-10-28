"""Ratha (#1891): the castle of the Bengalis trains the ratha (60 wood, 60 gold, 24 s; elite 18 s) and researches
Elite Ratha in the Imperial Age (slot 5: 800 food, 800 wood, 45 s), with the values of the AoE2 DE wiki infobox
"Ratha". The ratha stays in its ranged mode (the mode switch is not in the game program). The upgrade changes the live
and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("RATHA", "ELITE_RATHA", "ELITE_RATHA_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "BENGALIS" not in train.civs.MISSING[name] and "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_bengalis_trains_the_ratha():
    server, g = setup("BENGALIS", food=0, wood=60, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Ratha:60 wood · 60 gold · 24 s · queue 0/15 " in menu
    assert "Elite Ratha" not in menu                                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "RATHA"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ratha" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BENGALIS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["r"] = "RATHA"
    g.game.entities.setdefault("r", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Ratha:800 food · 800 wood · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATHA_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_RATHA_UPGRADE" in g.techs and g.soldiers["r"] == "ELITE_RATHA"
    assert combat.stats_command("r", "ELITE_RATHA", train.stats(g, "ELITE_RATHA")) in server.log   # Bengali cavalry (#2249)
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Elite Ratha:60 wood · 60 gold · 18 s · queue 0/15 " in menu
    assert ":Ratha:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_RATHA")
    assert train.queue(g, "Steve", CASTLE, "RATHA") is None
