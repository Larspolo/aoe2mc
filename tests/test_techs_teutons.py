"""Ironclad (#4112): the castle of the Teutons researches it in the Castle Age (slot 6: 400 wood, 350 gold, 60 s),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Teutons have it (the key "civ" of data/train.jsonl).
Its effect: siege weapons +4 melee armor."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["IRONCLAD"]) <= 50 and "TEUTONS" not in train.civs.MISSING["IRONCLAD"]
    assert "BRITONS" in train.civs.MISSING["IRONCLAD"]


def test_only_the_castle_of_the_teutons_researches_it():
    server, g = setup("TEUTONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Ironclad:400 wood · 350 gold · 60 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Ironclad" not in menus(server)[-1]


def test_the_effect_adds_melee_armor_to_siege_only():
    server, g = setup("TEUTONS", wood=3000, gold=3000, ages=2)
    ram = train.stats(g, "BATTERING_RAM")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "IRONCLAD")
    train.tick(g, 60)
    assert "IRONCLAD" in g.techs
    assert train.stats(g, "BATTERING_RAM").melee == ram.melee + 4
    assert train.stats(g, "KNIGHT").melee == knight.melee     # not siege
