"""Unique technology (#2044): the castle of the Franks researches Bearded Axe in the Castle Age. Only the Franks have it
(the key "civ" of data/train.jsonl). Its effect: the throwing axemen get more range."""
from menu_line import item
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_only_the_castle_of_the_franks_researches_it():
    server, g = setup("FRANKS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Bearded Axe").endswith(":Bearded Axe:" + text(g, "BEARDED_AXE") + "research")
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Bearded Axe" not in menus(server)[-1]


def test_the_effect_gives_the_throwing_axemen_range():
    server, g = setup("FRANKS", food=2000, wood=0, gold=2000, ages=2)
    before = train.stats(g, "THROWING_AXEMAN")
    assert train.queue(g, "Steve", CASTLE, "BEARDED_AXE")
    train.tick(g, train.TRAIN_TIMES["BEARDED_AXE"])
    assert "BEARDED_AXE" in g.techs
    assert train.stats(g, "THROWING_AXEMAN").range > before.range
    assert train.stats(g, "ELITE_THROWING_AXEMAN").range > combat.stats("ELITE_THROWING_AXEMAN").range
    assert train.stats(g, "ARBALESTER").range == combat.stats("ARBALESTER").range   # not a throwing axeman
