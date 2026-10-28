"""Conquistador (#1744): the castle of the Spanish trains the Conquistador (75 food, 60 gold, 26 s) and researches Elite
Conquistador in the Imperial Age (slot 5: 900 food, 600 gold, 60 s), with the values of the AoE2 DE wiki. The upgrade
changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["CONQUISTADOR"]) <= 50 and "SPANISH" not in train.civs.MISSING["CONQUISTADOR"]
    assert "BRITONS" in train.civs.MISSING["CONQUISTADOR"]


def test_the_castle_of_the_spanish_trains_the_conquistador():
    server, g = setup("SPANISH", food=75, wood=0, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_horse_spawn_egg:Conquistador:75 food · 60 gold · 26 s · queue 0/15 " in menu
    assert "Elite Conquistador" not in menu                            # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "CONQUISTADOR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Conquistador" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("SPANISH", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["cq"] = "CONQUISTADOR"
    g.game.entities.setdefault("cq", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Conquistador:900 food · 600 gold · 60 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_CONQUISTADOR_UPGRADE")
    train.tick(g, 60)
    assert "ELITE_CONQUISTADOR_UPGRADE" in g.techs and g.soldiers["cq"] == "ELITE_CONQUISTADOR"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:skeleton_horse_spawn_egg:Elite Conquistador:75 food · 60 gold · 24 s · queue 0/15 " in menu
    assert ":Conquistador:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CONQUISTADOR")
    assert train.queue(g, "Steve", CASTLE, "CONQUISTADOR") is None
