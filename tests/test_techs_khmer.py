"""Tusk Swords (#4107): the castle of the Khmer researches it in the Castle Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Khmer have it (the key "civ" of data/train.jsonl).
Its effect: battle elephants +3 attack."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_khmer_researches_it():
    server, g = setup("KHMER", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'TUSK_SWORDS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "TUSK_SWORDS") is None


def test_the_effect_adds_attack_to_battle_elephants_only():
    server, g = setup("KHMER", food=3000, wood=3000, gold=3000, ages=2)
    elephant = train.stats(g, "BATTLE_ELEPHANT")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "TUSK_SWORDS")
    train.tick(g, train.seconds(g, "TUSK_SWORDS", "CASTLE"))
    assert "TUSK_SWORDS" in g.techs
    assert train.stats(g, "BATTLE_ELEPHANT").attack > elephant.attack
    assert train.stats(g, "KNIGHT").attack == knight.attack     # not a battle elephant
