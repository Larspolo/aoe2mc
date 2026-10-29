"""Holcans (#4108): the castle of the Mayans researches it in the Imperial Age (slot 7: 750 food, 450 gold, 70 s),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Mayans have it (the key "civ" of data/train.jsonl).
Its effect: the eagle line and the Xolotl Warriors +40 HP. Like tests/test_farimba.py."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["HOLCANS"]) <= 50 and "MAYANS" not in train.civs.MISSING["HOLCANS"]
    assert "BRITONS" in train.civs.MISSING["HOLCANS"]


def test_only_the_castle_of_the_mayans_researches_it():
    server, g = setup("MAYANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Holcans:750 food · 450 gold · 70 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Holcans" not in menus(server)[-1]


def test_the_effect_adds_hp_to_the_eagle_line_and_xolotl_only():
    server, g = setup("MAYANS", food=3000, wood=0, gold=3000, ages=3)
    eagle = train.stats(g, "EAGLE_WARRIOR")
    xolotl = train.stats(g, "XOLOTL_WARRIOR")
    man = train.stats(g, "MAN_AT_ARMS")
    assert train.queue(g, "Steve", CASTLE, "HOLCANS")
    train.tick(g, 70)
    assert "HOLCANS" in g.techs
    assert train.stats(g, "EAGLE_WARRIOR").hp == eagle.hp + 40
    assert train.stats(g, "XOLOTL_WARRIOR").hp == xolotl.hp + 40
    assert train.stats(g, "MAN_AT_ARMS").hp == man.hp     # not the eagle line
