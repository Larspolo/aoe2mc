"""Counterweights (#4109): the castle of the Saracens researches it in the Imperial Age (slot 7: 650 food, 500 gold,
50 s), with the values of the AoE2 DE wiki ("Unique technology"). Only the Saracens have it (the key "civ" of
data/train.jsonl). Its effect: Trebuchets and the Mangonel line +15 % attack."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["COUNTERWEIGHTS"]) <= 50 and "SARACENS" not in train.civs.MISSING["COUNTERWEIGHTS"]
    assert "BRITONS" in train.civs.MISSING["COUNTERWEIGHTS"]


def test_only_the_castle_of_the_saracens_researches_it():
    server, g = setup("SARACENS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Counterweights:650 food · 500 gold · 50 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Counterweights" not in menus(server)[-1]


def test_the_effect_adds_attack_to_trebuchets_and_the_mangonel_line():
    server, g = setup("SARACENS", food=3000, gold=3000, ages=3)
    trebuchet = train.stats(g, "TREBUCHET")
    onager = train.stats(g, "ONAGER")
    scorpion = train.stats(g, "SCORPION")
    assert train.queue(g, "Steve", CASTLE, "COUNTERWEIGHTS")
    train.tick(g, 50)
    assert "COUNTERWEIGHTS" in g.techs
    assert train.stats(g, "TREBUCHET").attack == round(trebuchet.attack * 1.15)
    assert train.stats(g, "ONAGER").attack == round(onager.attack * 1.15)
    assert train.stats(g, "SCORPION").attack == scorpion.attack     # not in the line
