"""Unique technology of the Romans (#4220): the castle of the Romans researches Ballistas in the Castle Age, with the
values of the AoE2 DE wiki ("Unique technology"). Only the Romans have it (the key "civ" of data/train.jsonl).
Ballistas: Scorpions fire 33 % faster, Galleys +2 attack."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_romans_researches_ballistas():
    server, g = setup("ROMANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'BALLISTAS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "BALLISTAS") is None


def test_ballistas_speed_up_scorpions_and_add_attack_to_galleys_only():
    server, g = setup("ROMANS", food=3000, wood=3000, gold=3000, ages=2)
    scorpion = train.stats(g, "SCORPION")
    galley = train.stats(g, "GALLEY")
    archer = train.stats(g, "ARCHER")
    assert train.queue(g, "Steve", CASTLE, "BALLISTAS")
    train.tick(g, train.seconds(g, "BALLISTAS", "CASTLE"))
    assert "BALLISTAS" in g.techs
    assert train.stats(g, "SCORPION").reload < scorpion.reload
    assert train.stats(g, "GALLEY").attack == galley.attack + 2
    assert train.stats(g, "ARCHER") == archer       # not a scorpion or a galley
