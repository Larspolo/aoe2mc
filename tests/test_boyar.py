"""Boyar (#1721): the castle of the Slavs trains the boyar (60 food, 70 gold, 15 s) and researches Elite Boyar in the
Imperial Age (slot 5: 1000 food, 600 gold, 60 s), with the values of the AoE2 DE wiki infobox "Boyar (Age of Empires
II)". The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("BOYAR", "ELITE_BOYAR", "ELITE_BOYAR_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "SLAVS" not in train.civs.MISSING[name] and "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_slavs_trains_the_boyar():
    server, g = setup("SLAVS", food=60, wood=0, gold=70)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Boyar:60 food · 70 gold · 15 s · queue 0/15 " in menu
    assert "Elite Boyar" not in menu                                   # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "BOYAR"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Boyar" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("SLAVS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["by"] = "BOYAR"
    g.game.entities.setdefault("by", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Boyar:1000 food · 600 gold · 60 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_BOYAR_UPGRADE")
    train.tick(g, 60)
    assert "ELITE_BOYAR_UPGRADE" in g.techs and g.soldiers["by"] == "ELITE_BOYAR"
    assert combat.stats_command("by", "ELITE_BOYAR") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:horse_spawn_egg:Elite Boyar:60 food · 70 gold · 15 s · queue 0/15 " in menu
    assert ":Boyar:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_BOYAR")
    assert train.queue(g, "Steve", CASTLE, "BOYAR") is None
