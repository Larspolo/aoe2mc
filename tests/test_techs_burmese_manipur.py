"""Manipur Cavalry (#4218): the castle of the Burmese researches it in the Castle Age, with the values of the
AoE2 DE wiki ("Unique technology"). Only the Burmese have it (the key "civ" of data/train.jsonl).
Its effect: cavalry +4 attack vs. archers."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_burmese_researches_manipur_cavalry():
    server, g = setup("BURMESE", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'MANIPUR_CAVALRY')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "MANIPUR_CAVALRY") is None


def test_manipur_cavalry_adds_attack_to_cavalry_vs_archers_only():
    server, g = setup("BURMESE", food=3000, wood=3000, gold=3000, ages=2)
    knight = train.stats(g, "KNIGHT")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, "MANIPUR_CAVALRY")
    train.tick(g, train.seconds(g, "MANIPUR_CAVALRY", "CASTLE"))
    assert "MANIPUR_CAVALRY" in g.techs
    assert train.stats(g, "KNIGHT").bonus.get("archer", 0) == knight.bonus.get("archer", 0) + 4
    assert train.stats(g, "MILITIA").bonus.get("archer", 0) == militia.bonus.get("archer", 0)     # not cavalry
