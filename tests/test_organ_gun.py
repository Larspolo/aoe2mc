"""Organ Gun (#1890): the castle of the Portuguese trains the organ gun (80 wood, 70 gold, 28 s; 56 gold with the
Portuguese bonus in the menu) and researches Elite Organ Gun in the Imperial Age (slot 5: 1200 food, 500 gold, 45 s),
with the base values of the AoE2 DE wiki infobox "Organ Gun (Age of Empires II)". The upgrade changes the live and the
new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    for name in ("ORGAN_GUN", "ELITE_ORGAN_GUN", "ELITE_ORGAN_GUN_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "PORTUGUESE" not in train.civs.MISSING[name] and "BRITONS" in train.civs.MISSING[name]


def test_the_castle_of_the_portuguese_trains_the_organ_gun():
    server, g = setup("PORTUGUESE", food=0, wood=80, gold=70)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Organ Gun:80 wood · 56 gold · 28 s · queue 0/15 " in menu
    assert "Elite Organ" not in menu                                    # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, 0) == 1 and g.queues[rect][0]["name"] == "ORGAN_GUN"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Organ" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("PORTUGUESE", food=2000, wood=200, gold=2000, ages=3)
    g.soldiers["og"] = "ORGAN_GUN"
    g.game.entities.setdefault("og", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert " 5:book:Elite Organ Gun:1200 food · 500 gold · 45 s · research " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_ORGAN_GUN_UPGRADE")
    train.tick(g, 45)
    assert "ELITE_ORGAN_GUN_UPGRADE" in g.techs and g.soldiers["og"] == "ELITE_ORGAN_GUN"
    assert combat.stats_command("og", "ELITE_ORGAN_GUN") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 0:minecart:Elite Organ Gun:80 wood · 56 gold · 21 s · queue 0/15 " in menu
    assert ":Organ Gun:" not in menu and "5:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_ORGAN_GUN")
    assert train.queue(g, "Steve", CASTLE, "ORGAN_GUN") is None
