"""Unique technology of the Bengalis (#4216): the castle of the Bengalis researches Paiks in the Castle Age, with the
values of the AoE2 DE wiki ("Unique technology"). Only the Bengalis have it (the key "civ" of data/train.jsonl).
Paiks: rathas and elephants attack 20% faster (reload / 1.2)."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_bengalis_researches_paiks():
    server, g = setup("BENGALIS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'PAIKS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "PAIKS") is None


def test_paiks_speeds_up_rathas_and_elephants_only():
    server, g = setup("BENGALIS", food=3000, wood=3000, gold=3000, ages=2)
    elephant = train.stats(g, "BATTLE_ELEPHANT")
    ratha = train.stats(g, "RATHA")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "PAIKS")
    train.tick(g, train.seconds(g, "PAIKS", "CASTLE"))
    assert "PAIKS" in g.techs
    assert train.stats(g, "BATTLE_ELEPHANT").reload < elephant.reload
    assert train.stats(g, "RATHA").reload < ratha.reload
    assert train.stats(g, "KNIGHT").reload == knight.reload     # not an elephant
