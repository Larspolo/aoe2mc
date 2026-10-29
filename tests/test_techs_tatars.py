"""Silk Armor (Castle Age) and Timurid Siegecraft (Imperial Age), the unique technologies of the Tatars (#4100, #4096),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Tatars have them (the key "civ" of data/train.jsonl).
Silk Armor: scouts, steppe lancers and mounted archers +1/+1. Timurid Siegecraft: trebuchets +2 range."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["SILK_ARMOR"]) <= 50 and "TATARS" not in train.civs.MISSING["SILK_ARMOR"]
    assert "BRITONS" in train.civs.MISSING["SILK_ARMOR"]
    assert len(train.HELP["TIMURID_SIEGECRAFT"]) <= 50 and "TATARS" not in train.civs.MISSING["TIMURID_SIEGECRAFT"]
    assert "BRITONS" in train.civs.MISSING["TIMURID_SIEGECRAFT"]


def test_only_the_castle_of_the_tatars_researches_them():
    server, g = setup("TATARS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Silk Armor:400 wood · 300 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Silk Armor" not in menus(server)[-1]
    server, g = setup("TATARS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Timurid Siegecraft:500 wood · 400 gold · 50 s · research " in menus(server)[-1] + " "
    server, g = setup("FRANKS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Timurid Siegecraft" not in menus(server)[-1]


def test_silk_armor_adds_armor_to_scouts_lancers_and_mounted_archers():
    server, g = setup("TATARS", wood=3000, gold=3000, ages=2)
    scout = train.stats(g, "LIGHT_CAVALRY")
    archer = train.stats(g, "CAVALRY_ARCHER")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "SILK_ARMOR")
    train.tick(g, 40)
    assert "SILK_ARMOR" in g.techs
    assert train.stats(g, "LIGHT_CAVALRY").melee == scout.melee + 1
    assert train.stats(g, "CAVALRY_ARCHER").pierce == archer.pierce + 1
    assert train.stats(g, "KNIGHT") == knight                       # not a scout, lancer or archer


def test_timurid_siegecraft_adds_range_to_trebuchets_only():
    server, g = setup("TATARS", wood=3000, gold=3000, ages=3)
    trebuchet = train.stats(g, "TREBUCHET")
    mangonel = train.stats(g, "MANGONEL")
    assert train.queue(g, "Steve", CASTLE, "TIMURID_SIEGECRAFT")
    train.tick(g, 50)
    assert "TIMURID_SIEGECRAFT" in g.techs
    assert train.stats(g, "TREBUCHET").range == trebuchet.range + 2
    assert train.stats(g, "MANGONEL") == mangonel                   # not a trebuchet
