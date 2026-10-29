"""Ming Guang Armor (#4114): the castle of the Wei researches it in the Imperial Age. Its effect: more melee armor for
the mounted units (cavalry, camels and elephants), not for the militia."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)
NAME = "MING_GUANG_ARMOR"


def test_the_help_line_is_short():
    assert len(train.HELP[NAME]) <= 50


def test_the_castle_of_the_wei_offers_it_and_the_other_civilizations_do_not():
    server, g = setup("WEI", food=600, gold=450, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Ming Guang Armor:600 food · 450 gold · 65 s · research " in menus(server)[0]
    server, g = setup("BRITONS", food=600, gold=450, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ming Guang Armor" not in menus(server)[0]


def test_the_effect_adds_melee_armor_to_mounted_units_only():
    server, g = setup("WEI", food=3000, gold=3000, ages=3)
    knight = train.stats(g, "KNIGHT")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, NAME)
    train.tick(g, 65)
    assert NAME in g.techs
    assert train.stats(g, "KNIGHT").melee == knight.melee + 4
    assert train.stats(g, "MILITIA").melee == militia.melee     # not mounted
