"""Unique technologies of the Turks (#4101): the castle of the Turks researches Sipahi in the Castle Age and
Artillery in the Imperial Age, with the values of the AoE2 DE wiki ("Unique technology"). Only the Turks have them (the key "civ" of data/train.jsonl).
Sipahi: mounted archers +20 HP. Artillery: bombard towers, cannons and cannon galleons +2 range."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_turks_researches_sipahi():
    server, g = setup("TURKS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'SIPAHI')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "SIPAHI") is None


def test_only_the_castle_of_the_turks_researches_artillery():
    server, g = setup("TURKS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'ARTILLERY')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "ARTILLERY") is None


def test_sipahi_adds_hp_to_mounted_archers_only():
    server, g = setup("TURKS", food=3000, wood=3000, gold=3000, ages=2)
    cavalry_archer = train.stats(g, "CAVALRY_ARCHER")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "SIPAHI")
    train.tick(g, train.seconds(g, "SIPAHI", "CASTLE"))
    assert "SIPAHI" in g.techs
    assert train.stats(g, "CAVALRY_ARCHER").hp > cavalry_archer.hp
    assert train.stats(g, "ARCHER").hp == archer.hp     # not mounted


def test_artillery_adds_range_to_bombard_towers_and_cannons():
    server, g = setup("TURKS", food=3000, wood=3000, gold=3000, ages=3)
    cannon = train.stats(g, "BOMBARD_CANNON")
    tower = build.values(g, "BOMBARD_TOWER")
    hand = train.stats(g, "HAND_CANNONEER")
    assert train.queue(g, "Steve", CASTLE, "ARTILLERY")
    train.tick(g, train.seconds(g, "ARTILLERY", "CASTLE"))
    assert "ARTILLERY" in g.techs
    assert train.stats(g, "BOMBARD_CANNON").range > cannon.range
    assert build.values(g, "BOMBARD_TOWER").range > tower.range
    assert train.stats(g, "HAND_CANNONEER").range == hand.range     # not a bombard
