"""Furor Celtica (#2043): the castle of the Celts researches it in the Imperial Age (slot 7: 750 food, 450 gold, 50 s,
AoE2 DE wiki "Furor Celtica"). Siege weapons get 40 % more hit points. Only the Celts have it (the key "civ")."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.CIV_TECHS["FUROR_CELTICA"] == "CELTS"
    assert len(train.HELP["FUROR_CELTICA"]) <= 50 and "CELTS" not in train.civs.MISSING["FUROR_CELTICA"]
    assert "BRITONS" in train.civs.MISSING["FUROR_CELTICA"]


def test_only_the_castle_of_the_celts_researches_it():
    server, g = setup("CELTS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Furor Celtica:750 food · 450 gold · 50 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Furor Celtica" not in menus(server)[-1]


def test_siege_weapons_get_more_hit_points():
    server, g = setup("CELTS", food=800, wood=0, gold=500, ages=3)
    before = train.stats(g, "MANGONEL").hp
    assert train.queue(g, "Steve", CASTLE, "FUROR_CELTICA")
    train.tick(g, 50)
    assert "FUROR_CELTICA" in g.techs
    assert train.stats(g, "MANGONEL").hp == round(before * 1.4)
    assert train.stats(g, "ARAMBAI").hp == 60                 # not siege: unchanged
