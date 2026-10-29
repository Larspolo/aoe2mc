"""Unique technologies of the Incas (#4274): the castle of the Incas researches Andean Sling in the Castle Age, with the
values of the AoE2 DE wiki ("Unique technology"). Only the Incas have it (the key "civ" of data/train.jsonl).
Andean Sling: slingers +1 attack. Skirmishers and Slingers have no minimum range in the data, so none is removed here."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_incas_researches_andean_sling():
    server, g = setup("INCAS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'ANDEAN_SLING')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "ANDEAN_SLING") is None


def test_fabric_shields_stays_in_the_castle_menu_of_the_incas():
    server, g = setup("INCAS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'FABRIC_SHIELDS')}:" in menus(server)[-1]
    assert label(g, "ANDEAN_SLING") is not None


def test_andean_sling_adds_attack_to_slingers_only():
    server, g = setup("INCAS", food=3000, wood=3000, gold=3000, ages=2)
    slinger = train.stats(g, "SLINGER")
    skirmisher = train.stats(g, "SKIRMISHER")
    assert train.queue(g, "Steve", CASTLE, "ANDEAN_SLING")
    train.tick(g, train.seconds(g, "ANDEAN_SLING", "CASTLE"))
    assert "ANDEAN_SLING" in g.techs
    assert train.stats(g, "SLINGER").attack == combat.stats("SLINGER").attack + 1
    assert train.stats(g, "SKIRMISHER").attack == skirmisher.attack     # not a slinger
    assert slinger.attack == combat.stats("SLINGER").attack
