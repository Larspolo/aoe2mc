"""Frontier Guards (#4105): the castle of the Gurjaras researches it in the Imperial Age (slot 7: 800 food, 700 gold,
60 s), with the values of the AoE2 DE wiki ("Unique technology"). Only the Gurjaras have it (the key "civ" of
data/train.jsonl). Its effect: Camel Riders and Elephant Archers +4 melee armor."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["FRONTIER_GUARDS"]) <= 50 and "GURJARAS" not in train.civs.MISSING["FRONTIER_GUARDS"]
    assert "BRITONS" in train.civs.MISSING["FRONTIER_GUARDS"]


def test_only_the_castle_of_the_gurjaras_researches_it():
    server, g = setup("GURJARAS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Frontier Guards:800 food · 700 gold · 60 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Frontier Guards" not in menus(server)[-1]


def test_the_effect_adds_melee_armor_to_camels_and_elephant_archers_only():
    server, g = setup("GURJARAS", food=3000, gold=3000, ages=3)
    camel = train.stats(g, "HEAVY_CAMEL_RIDER")
    archer = train.stats(g, "ELEPHANT_ARCHER")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "FRONTIER_GUARDS")
    train.tick(g, 60)
    assert "FRONTIER_GUARDS" in g.techs
    assert train.stats(g, "HEAVY_CAMEL_RIDER").melee == camel.melee + 4
    assert train.stats(g, "ELEPHANT_ARCHER").melee == archer.melee + 4
    assert train.stats(g, "KNIGHT") == knight                       # not a camel or an elephant
