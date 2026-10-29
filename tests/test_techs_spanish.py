"""Supremacy (#4111): the castle of the Spanish researches it in the Imperial Age,
with the values of the AoE2 DE wiki ("Unique technology"). Only the Spanish have it (the key "civ" of data/train.jsonl).
Its effect: villagers +6 attack, +2/+2 armor, +40 HP. The test follows tests/test_farimba.py (#2046)."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_the_spanish_researches_it():
    server, g = setup("SPANISH", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, 'SUPREMACY')}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, "SUPREMACY") is None


def test_the_effect_adds_attack_and_hp_to_villagers_only():
    server, g = setup("SPANISH", food=3000, wood=3000, gold=3000, ages=3)
    villager = train.stats(g, "VILLAGER")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, "SUPREMACY")
    train.tick(g, train.seconds(g, "SUPREMACY", "CASTLE"))
    assert "SUPREMACY" in g.techs
    assert train.stats(g, "VILLAGER").attack > villager.attack
    assert train.stats(g, "VILLAGER").hp > villager.hp
    assert train.stats(g, "MILITIA").attack == militia.attack     # not villagers
