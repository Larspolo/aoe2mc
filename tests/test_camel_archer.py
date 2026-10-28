"""Camel Archer (#1723): the castle of the Berbers trains the camel archer (50 wood, 60 gold, 25 s) and researches
Elite Camel Archer in the Imperial Age (slot 5: 1000 wood, 500 gold, 45 s), with the values of the AoE2 DE wiki
"Camel Archer (Age of Empires II)". The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("CAMEL_ARCHER", "ELITE_CAMEL_ARCHER", "ELITE_CAMEL_ARCHER_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_berbers_trains_the_camel_archer():
    server, g = setup("BERBERS", wood=50, gold=60)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:camel_spawn_egg:Camel Archer:50 wood · 60 gold · 25 s · queue 0/15 " in menu
    assert "Elite Camel" not in menu                                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "CAMEL_ARCHER"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Camel" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("BERBERS", wood=2000, gold=2000, ages=3)
    g.soldiers["ca"] = "CAMEL_ARCHER"
    g.game.entities.setdefault("ca", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Camel Archer:1000 wood · 500 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_CAMEL_ARCHER_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_CAMEL_ARCHER_UPGRADE" in g.techs and g.soldiers["ca"] == "ELITE_CAMEL_ARCHER"
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:camel_spawn_egg:Elite Camel Archer:50 wood · 60 gold · 25 s · queue 0/15 " in menu
    assert ":Camel Archer:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_CAMEL_ARCHER")
    assert train.queue(g, "Steve", CASTLE, "CAMEL_ARCHER") is None
