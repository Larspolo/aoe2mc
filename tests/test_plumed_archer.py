"""Plumed Archer (#1887): the castle of the Mayans trains the Plumed Archer (55 wood, 55 gold, 16 s) and
researches Elite Plumed Archer in the Imperial Age (slot 5: 700 food, 1000 wood, 45 s), with the values of the AoE2 DE
wiki. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["PLUMED_ARCHER"]) <= 50 and "MAYANS" not in train.civs.MISSING["PLUMED_ARCHER"]
    assert "BRITONS" in train.civs.MISSING["PLUMED_ARCHER"]


def test_the_castle_of_the_mayans_trains_the_plumed_archer():
    server, g = setup("MAYANS", food=0, wood=44, gold=44)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Plumed Archer:44 wood · 44 gold · 16 s · queue 0/15 " in menu  # the Mayan bonus, Castle Age
    assert "Elite Plumed" not in menu                                     # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "PLUMED_ARCHER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Plumed" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("MAYANS", food=2000, wood=2000, gold=2000, ages=3)
    g.soldiers["pa"] = "PLUMED_ARCHER"
    g.game.entities.setdefault("pa", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Plumed Archer:700 food · 1000 wood · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_PLUMED_ARCHER_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_PLUMED_ARCHER_UPGRADE" in g.techs and g.soldiers["pa"] == "ELITE_PLUMED_ARCHER"
    assert combat.stats_command("pa", "ELITE_PLUMED_ARCHER") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_spawn_egg:Elite Plumed Archer:39 wood · 39 gold · 16 s · queue 0/15 " in menu  # the Imperial Age bonus
    assert ":Plumed Archer:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_PLUMED_ARCHER")
    assert train.queue(g, "Steve", CASTLE, "PLUMED_ARCHER") is None
