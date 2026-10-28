"""Composite Bowman (#1759): the castle of the Armenians trains the Composite Bowman (35 wood, 45 gold, 12 s) and
researches Elite Composite Bowman in the Imperial Age (slot 5: 600 wood, 500 gold, 45 s), with the values of the AoE2 DE
wiki. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["COMPOSITE_BOWMAN"]) <= 50 and "ARMENIANS" not in train.civs.MISSING["COMPOSITE_BOWMAN"]
    assert "BRITONS" in train.civs.MISSING["COMPOSITE_BOWMAN"]


def test_the_castle_of_the_armenians_trains_the_composite_bowman():
    server, g = setup("ARMENIANS", food=0, wood=35, gold=45)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Composite Bowman:35 wood · 45 gold · 12 s · queue 0/15 " in menu
    assert "Elite Composite" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "COMPOSITE_BOWMAN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Composite" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ARMENIANS", food=0, wood=2000, gold=2000, ages=3)
    g.soldiers["cb"] = "COMPOSITE_BOWMAN"
    g.game.entities.setdefault("cb", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Composite Bowman:600 wood · 500 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_COMPOSITE_BOWMAN_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_COMPOSITE_BOWMAN_UPGRADE" in g.techs and g.soldiers["cb"] == "ELITE_COMPOSITE_BOWMAN"
    assert combat.stats_command("cb", "ELITE_COMPOSITE_BOWMAN") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Elite Composite Bowman:35 wood · 45 gold · 10 s · queue 0/15 " in menu
    assert ":Composite Bowman:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_COMPOSITE_BOWMAN")
    assert train.queue(g, "Steve", CASTLE, "COMPOSITE_BOWMAN") is None
