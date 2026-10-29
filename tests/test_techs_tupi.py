"""Unique technology of the Tupi (#4223): the castle of the Tupi researches Caciques in the Castle Age, with the values of
the AoE2 DE wiki ("Unique technology"). Only the Tupi have it (the key "civ" of data/train.jsonl).
Caciques: Champi scouts, slingers and Xolotl Warriors attack 25% faster."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_tupi_researches_caciques():
    server, g = setup("TUPI", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'CACIQUES')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "CACIQUES") is None


def test_caciques_speeds_up_slingers_and_champi_scouts_only():
    server, g = setup("TUPI", food=3000, wood=3000, gold=3000, ages=2)
    slinger = train.stats(g, "SLINGER")
    scout = train.stats(g, "CHAMPI_SCOUT")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "CACIQUES")
    train.tick(g, train.seconds(g, "CACIQUES", "CASTLE"))
    assert "CACIQUES" in g.techs
    assert train.stats(g, "SLINGER").reload < slinger.reload
    assert train.stats(g, "CHAMPI_SCOUT").reload < scout.reload
    assert train.stats(g, "ARCHER").reload == archer.reload     # not in the list
