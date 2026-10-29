"""Silk Armor (Castle Age) and Timurid Siegecraft (Imperial Age), the unique technologies of the Tatars (#4100, #4096),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Tatars have them (the key "civ" of data/train.jsonl).
Silk Armor: scouts, steppe lancers and mounted archers +1/+1. Timurid Siegecraft: trebuchets +2 range."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_tatars_researches_them():
    server, g = setup("TATARS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'SILK_ARMOR')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "SILK_ARMOR") is None
    server, g = setup("TATARS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'TIMURID_SIEGECRAFT')}:" in menus(server)[-1]
    server, g = setup("FRANKS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "TIMURID_SIEGECRAFT") is None


def test_silk_armor_adds_armor_to_scouts_lancers_and_mounted_archers():
    server, g = setup("TATARS", food=3000, wood=3000, gold=3000, ages=2)
    scout = train.stats(g, "LIGHT_CAVALRY")
    archer = train.stats(g, "CAVALRY_ARCHER")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "SILK_ARMOR")
    train.tick(g, train.seconds(g, "SILK_ARMOR", "CASTLE"))
    assert "SILK_ARMOR" in g.techs
    assert train.stats(g, "LIGHT_CAVALRY").melee > scout.melee
    assert train.stats(g, "CAVALRY_ARCHER").pierce > archer.pierce
    assert train.stats(g, "KNIGHT") == knight                       # not a scout, lancer or archer


def test_timurid_siegecraft_adds_range_to_trebuchets_only():
    server, g = setup("TATARS", food=3000, wood=3000, gold=3000, ages=3)
    trebuchet = train.stats(g, "TREBUCHET")
    mangonel = train.stats(g, "MANGONEL")
    assert train.queue(g, "Steve", CASTLE, "TIMURID_SIEGECRAFT")
    train.tick(g, train.seconds(g, "TIMURID_SIEGECRAFT", "CASTLE"))
    assert "TIMURID_SIEGECRAFT" in g.techs
    assert train.stats(g, "TREBUCHET").range > trebuchet.range
    assert train.stats(g, "MANGONEL") == mangonel                   # not a trebuchet
