"""Frontier Guards (#4105): the castle of the Gurjaras researches it in the Imperial Age, with the values of the AoE2 DE wiki ("Unique technology"). Only the Gurjaras have it (the key "civ" of
data/train.jsonl). Its effect: Camel Riders and Elephant Archers +4 melee armor."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_gurjaras_researches_it():
    server, g = setup("GURJARAS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'FRONTIER_GUARDS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "FRONTIER_GUARDS") is None


def test_the_effect_adds_melee_armor_to_camels_and_elephant_archers_only():
    server, g = setup("GURJARAS", food=3000, wood=3000, gold=3000, ages=3)
    camel = train.stats(g, "HEAVY_CAMEL_RIDER")
    archer = train.stats(g, "ELEPHANT_ARCHER")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "FRONTIER_GUARDS")
    train.tick(g, train.seconds(g, "FRONTIER_GUARDS", "CASTLE"))
    assert "FRONTIER_GUARDS" in g.techs
    assert train.stats(g, "HEAVY_CAMEL_RIDER").melee > camel.melee
    assert train.stats(g, "ELEPHANT_ARCHER").melee > archer.melee
    assert train.stats(g, "KNIGHT") == knight                       # not a camel or an elephant
