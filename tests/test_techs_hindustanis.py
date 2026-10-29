"""Unique technology of the Hindustanis (#4106, epic #4096): the castle of the Hindustanis researches Shatagni in the
Imperial Age (AoE2 DE wiki "Unique technology"). Its effect: Hand Cannoneers +2 range."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)
NAME = "SHATAGNI"


def test_only_the_hindustanis_have_shatagni():
    assert NAME in train.trains(setup("HINDUSTANIS", ages=3)[1], "CASTLE")
    assert NAME not in train.trains(setup("BRITONS", ages=3)[1], "CASTLE")


def test_the_help_line_is_short_enough_for_the_menu():
    assert len(train.HELP[NAME]) <= 50


def test_the_castle_menu_has_shatagni_for_the_hindustanis_only():
    server, g = setup("HINDUSTANIS", food=3000, gold=3000, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Shatagni") == "7:book:Shatagni:500 food · 650 gold · 40 s · research"
    server, g = setup("BRITONS", food=3000, gold=3000, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Shatagni" not in menus(server)[-1]


def test_the_effect_adds_range_to_hand_cannoneers_only():
    server, g = setup("HINDUSTANIS", food=3000, gold=3000, ages=3)
    cannoneer = train.stats(g, "HAND_CANNONEER")
    arbalester = train.stats(g, "ARBALESTER")
    assert train.queue(g, "Steve", CASTLE, NAME)
    train.tick(g, 40)
    assert NAME in g.techs
    assert train.stats(g, "HAND_CANNONEER").range == cannoneer.range + 2
    assert train.stats(g, "ARBALESTER") == arbalester
