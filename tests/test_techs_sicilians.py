"""Hauberk (#4110): the castle of the Sicilians researches it in the Imperial Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Sicilians have it (the key "civ" of data/train.jsonl).
Its effect: knights +1 melee and +2 pierce armor, not the scout cavalry."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_sicilians_researches_it():
    server, g = setup("SICILIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'HAUBERK')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "HAUBERK") is None


def test_the_effect_adds_armor_to_knights_only():
    server, g = setup("SICILIANS", food=3000, wood=3000, gold=3000, ages=3)
    cavalier = train.stats(g, "CAVALIER")
    scout = train.stats(g, "SCOUT_CAVALRY")
    assert train.queue(g, "Steve", CASTLE, "HAUBERK")
    train.tick(g, train.seconds(g, "HAUBERK", "CASTLE"))
    assert "HAUBERK" in g.techs
    assert train.stats(g, "CAVALIER").pierce > cavalier.pierce
    assert train.stats(g, "CAVALIER").melee > cavalier.melee
    assert train.stats(g, "SCOUT_CAVALRY").pierce == scout.pierce     # not a knight
