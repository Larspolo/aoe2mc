"""Howdah (#4104): the castle of the Burmese researches it in the Imperial Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Burmese have it (the key "civ" of data/train.jsonl).
Its effect: battle elephants +1 melee and +1 pierce armor."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_burmese_researches_it():
    server, g = setup("BURMESE", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'HOWDAH')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "HOWDAH") is None


def test_the_effect_adds_armor_to_battle_elephants_only():
    server, g = setup("BURMESE", food=3000, wood=3000, gold=3000, ages=3)
    elephant = train.stats(g, "ELITE_BATTLE_ELEPHANT")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "HOWDAH")
    train.tick(g, train.seconds(g, "HOWDAH", "CASTLE"))
    assert "HOWDAH" in g.techs
    assert train.stats(g, "ELITE_BATTLE_ELEPHANT").pierce > elephant.pierce
    assert train.stats(g, "KNIGHT").pierce == knight.pierce     # not a battle elephant
