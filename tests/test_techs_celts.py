"""Unique technology of the Celts (#4222): the castle of the Celts researches Stronghold in the Castle Age, with the
values of the AoE2 DE wiki ("Unique technology"). Only the Celts have it (the key "civ" of data/train.jsonl).
Stronghold: castles and towers fire 33 % faster."""
from test_train_castle import menus, setup

from game import build, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_celts_researches_stronghold():
    server, g = setup("CELTS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'STRONGHOLD')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "STRONGHOLD") is None


def test_stronghold_speeds_up_castles_and_towers_only():
    server, g = setup("CELTS", food=3000, wood=3000, gold=3000, ages=2)
    castle = build.values(g, "CASTLE")
    tower = build.values(g, "WATCH_TOWER")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "STRONGHOLD")
    train.tick(g, train.seconds(g, "STRONGHOLD", "CASTLE"))
    assert "STRONGHOLD" in g.techs
    assert build.values(g, "CASTLE").reload < castle.reload
    assert build.values(g, "WATCH_TOWER").reload < tower.reload
    assert train.stats(g, "ARCHER").reload == archer.reload     # not a building
