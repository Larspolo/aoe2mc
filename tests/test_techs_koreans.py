"""Unique technology of the Koreans (#4219): the castle of the Koreans researches Shinkichon in the Imperial Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Koreans have it (the key "civ" of data/train.jsonl).
Shinkichon: Rocket Carts and Turtle Ships +1 range."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_koreans_researches_shinkichon():
    server, g = setup("KOREANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'SHINKICHON')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "SHINKICHON") is None


def test_shinkichon_adds_range_to_rocket_carts_and_turtle_ships_only():
    server, g = setup("KOREANS", food=3000, wood=3000, gold=3000, ages=3)
    cart = train.stats(g, "ROCKET_CART")
    turtle = train.stats(g, "TURTLE_SHIP")
    scorpion = train.stats(g, "SCORPION")
    assert train.queue(g, "Steve", CASTLE, "SHINKICHON")
    train.tick(g, train.seconds(g, "SHINKICHON", "CASTLE"))
    assert "SHINKICHON" in g.techs
    assert train.stats(g, "ROCKET_CART").range == cart.range + 1
    assert train.stats(g, "TURTLE_SHIP").range == turtle.range + 1
    assert train.stats(g, "SCORPION").range == scorpion.range     # not a rocket cart or a turtle ship
