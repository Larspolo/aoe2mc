"""Recurve Bow (#2045): the castle of the Magyars researches it in the Imperial Age (slot 7: 600 wood, 400 gold, 40 s,
the AoE2 DE wiki "Recurve Bow"). Mounted archers get +1 attack and +1 range; foot archers do not. Only the Magyars
have it (the key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["civ"]["RECURVE_BOW"] == "MAGYARS"
    assert len(train.HELP["RECURVE_BOW"]) <= 50 and "MAGYARS" not in train.civs.MISSING["RECURVE_BOW"]
    assert "BRITONS" in train.civs.MISSING["RECURVE_BOW"]


def test_only_the_castle_of_the_magyars_researches_it():
    server, g = setup("MAGYARS", wood=600, gold=400, ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Recurve Bow:600 wood · 400 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Recurve Bow" not in menus(server)[-1]


def test_the_effect_changes_the_mounted_archers_only():
    server, g = setup("MAGYARS", wood=600, gold=400, ages=3)
    cavalry = train.stats(g, "CAVALRY_ARCHER")
    foot = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "RECURVE_BOW")
    train.tick(g, 40)
    assert "RECURVE_BOW" in g.techs
    after = train.stats(g, "CAVALRY_ARCHER")
    assert after.attack == cavalry.attack + 1 and after.range == cavalry.range + 1
    assert train.stats(g, "ARCHER") == foot
