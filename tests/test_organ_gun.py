"""Organ Gun (#1890): the castle of the Portuguese trains the organ gun (less gold with the Portuguese bonus in the menu)
and researches Elite Organ Gun in the Imperial Age, with the base values of the AoE2 DE wiki infobox "Organ Gun (Age of
Empires II)" (the data). The upgrade changes the live and the new units."""
from menu_line import item
from test_train_castle import menus, setup

import buildings
from game import combat, train

CASTLE = (12, 4)
CIV = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING["ORGAN_GUN"]))   # the Portuguese
UPGRADE = "ELITE_ORGAN_GUN_UPGRADE"


def test_the_castle_of_the_portuguese_trains_the_organ_gun():
    server, g = setup(CIV, food=0, wood=1000, gold=1000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    gold = train.price(g, "ORGAN_GUN")["gold"]                          # with the Portuguese bonus
    unit = item(menu, "Organ Gun")
    assert unit.startswith(f"{train.SLOTS['ORGAN_GUN']}:") and f" · {gold} gold · " in unit and unit.endswith("queue 0/15")
    assert "Elite Organ" not in menu                                    # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.SLOTS["ORGAN_GUN"]) == 1 and g.queues[rect][0]["name"] == "ORGAN_GUN"
    server, g = setup(min(train.civs.MISSING["ORGAN_GUN"]), ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Organ" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    assert CIV not in train.civs.MISSING[UPGRADE]
    server, g = setup(CIV, food=5000, wood=1000, gold=5000, ages=3)
    g.soldiers["og"] = "ORGAN_GUN"
    g.game.entities.setdefault("og", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    up = item(menus(server)[-1], "Elite Organ Gun")
    assert up.startswith(f"{train.SLOTS[UPGRADE]}:") and up.endswith(" · research")
    assert train.queue(g, "Steve", CASTLE, UPGRADE)
    train.tick(g, train.seconds(g, UPGRADE, "CASTLE"))
    assert UPGRADE in g.techs and g.soldiers["og"] == "ELITE_ORGAN_GUN"
    assert combat.stats_command("og", "ELITE_ORGAN_GUN") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1]
    unit = item(menu, "Elite Organ Gun")                                # one item: the unit, no upgrade
    assert unit.startswith(f"{train.SLOTS['ORGAN_GUN']}:") and unit.endswith("queue 0/15")
    assert ":Organ Gun:" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_ORGAN_GUN")
    assert train.queue(g, "Steve", CASTLE, "ORGAN_GUN") is None
