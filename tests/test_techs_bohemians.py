"""Unique technologies of the Bohemians (#4217, epic #4096): the castle of the Bohemians researches Wagenburg Tactics in
the Castle Age, with the values of the AoE2 DE wiki ("Unique technology"). Only the Bohemians have it (the key "civ" of
data/train.jsonl). Wagenburg Tactics: gunpowder units walk 10 % faster."""
import pytest
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_bohemians_researches_wagenburg_tactics():
    server, g = setup("BOHEMIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'WAGENBURG_TACTICS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "WAGENBURG_TACTICS") is None


def test_wagenburg_tactics_makes_gunpowder_units_walk_faster():
    server, g = setup("BOHEMIANS", food=3000, wood=3000, gold=3000, ages=2)
    before = train.speed(g, "HAND_CANNONEER")
    assert train.speed(g, "MILITIA") == 1
    assert train.queue(g, "Steve", CASTLE, "WAGENBURG_TACTICS")
    train.tick(g, train.seconds(g, "WAGENBURG_TACTICS", "CASTLE"))
    assert "WAGENBURG_TACTICS" in g.techs
    assert train.speed(g, "HAND_CANNONEER") == pytest.approx(before * 1.1)
    assert train.speed(g, "MILITIA") == 1                                 # not gunpowder
