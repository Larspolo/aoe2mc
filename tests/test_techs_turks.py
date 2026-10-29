"""Unique technologies of the Turks (#4101): the castle of the Turks researches Sipahi in the Castle Age (slot 6: 350
food, 150 gold, 60 s) and Artillery in the Imperial Age (slot 7: 600 food, 650 gold, 40 s), with the values of the AoE2
DE wiki ("Unique technology"). Only the Turks have them (the key "civ" of data/train.jsonl).
Sipahi: mounted archers +20 HP. Artillery: bombard towers, cannons and cannon galleons +2 range."""
from test_farimba import menus, setup

from game import build, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["SIPAHI"]) <= 50 and "TURKS" not in train.civs.MISSING["SIPAHI"]
    assert "BRITONS" in train.civs.MISSING["SIPAHI"]
    assert len(train.HELP["ARTILLERY"]) <= 50 and "TURKS" not in train.civs.MISSING["ARTILLERY"]
    assert "BRITONS" in train.civs.MISSING["ARTILLERY"]


def test_only_the_castle_of_the_turks_researches_sipahi():
    server, g = setup("TURKS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Sipahi:350 food · 150 gold · 60 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Sipahi" not in menus(server)[-1]


def test_only_the_castle_of_the_turks_researches_artillery():
    server, g = setup("TURKS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Artillery:600 food · 650 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Artillery" not in menus(server)[-1]


def test_sipahi_adds_hp_to_mounted_archers_only():
    server, g = setup("TURKS", food=3000, gold=3000, ages=2)
    cavalry_archer = train.stats(g, "CAVALRY_ARCHER")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "SIPAHI")
    train.tick(g, 60)
    assert "SIPAHI" in g.techs
    assert train.stats(g, "CAVALRY_ARCHER").hp == cavalry_archer.hp + 20
    assert train.stats(g, "ARCHER").hp == archer.hp     # not mounted


def test_artillery_adds_range_to_bombard_towers_and_cannons():
    server, g = setup("TURKS", food=3000, gold=3000, ages=3)
    cannon = train.stats(g, "BOMBARD_CANNON")
    tower = build.values(g, "BOMBARD_TOWER")
    hand = train.stats(g, "HAND_CANNONEER")
    assert train.queue(g, "Steve", CASTLE, "ARTILLERY")
    train.tick(g, 40)
    assert "ARTILLERY" in g.techs
    assert train.stats(g, "BOMBARD_CANNON").range == cannon.range + 2
    assert build.values(g, "BOMBARD_TOWER").range == tower.range + 2
    assert train.stats(g, "HAND_CANNONEER").range == hand.range     # not a bombard
