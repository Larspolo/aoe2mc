"""Counterweights (#4109): the castle of the Saracens researches it in the Imperial Age, with the values of the AoE2 DE wiki ("Unique technology"). Only the Saracens have it (the key "civ" of
data/train.jsonl). Its effect: Trebuchets and the Mangonel line +15 % attack."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_saracens_researches_it():
    server, g = setup("SARACENS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'COUNTERWEIGHTS')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "COUNTERWEIGHTS") is None


def test_the_effect_adds_attack_to_trebuchets_and_the_mangonel_line():
    server, g = setup("SARACENS", food=3000, wood=3000, gold=3000, ages=3)
    trebuchet = train.stats(g, "TREBUCHET")
    onager = train.stats(g, "ONAGER")
    scorpion = train.stats(g, "SCORPION")
    assert train.queue(g, "Steve", CASTLE, "COUNTERWEIGHTS")
    train.tick(g, train.seconds(g, "COUNTERWEIGHTS", "CASTLE"))
    assert "COUNTERWEIGHTS" in g.techs
    assert train.stats(g, "TREBUCHET").attack > trebuchet.attack
    assert train.stats(g, "ONAGER").attack > onager.attack
    assert train.stats(g, "SCORPION").attack == scorpion.attack     # not in the line
