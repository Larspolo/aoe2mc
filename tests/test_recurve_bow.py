"""Recurve Bow (#2045): the castle of the Magyars researches it in the Imperial Age. Mounted archers get more attack and
range; foot archers do not. Only the Magyars have it (the key "civ" of data/train.jsonl)."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_only_the_castle_of_the_magyars_researches_it():
    server, g = setup("MAGYARS", wood=2000, gold=2000, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Recurve Bow").endswith(" · research")
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Recurve Bow" not in menus(server)[-1]


def test_the_effect_changes_the_mounted_archers_only():
    server, g = setup("MAGYARS", wood=2000, gold=2000, ages=3)
    cavalry = train.stats(g, "CAVALRY_ARCHER")
    foot = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "RECURVE_BOW")
    train.tick(g, train.seconds(g, "RECURVE_BOW", "CASTLE"))
    assert "RECURVE_BOW" in g.techs
    after = train.stats(g, "CAVALRY_ARCHER")
    assert after != cavalry and after.attack >= cavalry.attack and after.range >= cavalry.range
    assert train.stats(g, "ARCHER") == foot
