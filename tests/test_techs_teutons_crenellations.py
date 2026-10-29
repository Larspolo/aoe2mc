"""Unique technology of the Teutons (#4221): the castle of the Teutons researches Crenellations in the Imperial Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Teutons have it (the key "civ" of data/train.jsonl).
Crenellations: castles +3 range."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_teutons_researches_crenellations():
    server, g = setup("TEUTONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'CRENELLATIONS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "CRENELLATIONS") is None


def test_crenellations_adds_range_to_the_castle():
    server, g = setup("TEUTONS", food=3000, wood=3000, gold=3000, ages=3)
    g.stock.update(stone=3000)
    castle = build.values(g, "CASTLE").range
    tower = build.values(g, "WATCH_TOWER").range
    assert train.queue(g, "Steve", CASTLE, "CRENELLATIONS")
    train.tick(g, train.seconds(g, "CRENELLATIONS", "CASTLE"))
    assert "CRENELLATIONS" in g.techs
    assert build.values(g, "CASTLE").range == castle + 3
    assert build.values(g, "WATCH_TOWER").range == tower     # not a castle
