"""Holcans (#4108): the castle of the Mayans researches it in the Imperial Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Mayans have it (the key "civ" of data/train.jsonl).
Its effect: the eagle line and the Xolotl Warriors +40 HP. Like tests/test_farimba.py."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_mayans_researches_it():
    server, g = setup("MAYANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'HOLCANS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "HOLCANS") is None


def test_the_effect_adds_hp_to_the_eagle_line_and_xolotl_only():
    server, g = setup("MAYANS", food=3000, wood=3000, gold=3000, ages=3)
    eagle = train.stats(g, "EAGLE_WARRIOR")
    xolotl = train.stats(g, "XOLOTL_WARRIOR")
    man = train.stats(g, "MAN_AT_ARMS")
    assert train.queue(g, "Steve", CASTLE, "HOLCANS")
    train.tick(g, train.seconds(g, "HOLCANS", "CASTLE"))
    assert "HOLCANS" in g.techs
    assert train.stats(g, "EAGLE_WARRIOR").hp > eagle.hp
    assert train.stats(g, "XOLOTL_WARRIOR").hp > xolotl.hp
    assert train.stats(g, "MAN_AT_ARMS").hp == man.hp     # not the eagle line
