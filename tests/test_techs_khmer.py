"""Tusk Swords (#4107): the castle of the Khmer researches it in the Castle Age (slot 6: 300 wood, 450 gold, 40 s),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Khmer have it (the key "civ" of data/train.jsonl).
Its effect: battle elephants +3 attack."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["TUSK_SWORDS"]) <= 50 and "KHMER" not in train.civs.MISSING["TUSK_SWORDS"]
    assert "BRITONS" in train.civs.MISSING["TUSK_SWORDS"]


def test_only_the_castle_of_the_khmer_researches_it():
    server, g = setup("KHMER", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Tusk Swords:300 wood · 450 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Tusk Swords" not in menus(server)[-1]


def test_the_effect_adds_attack_to_battle_elephants_only():
    server, g = setup("KHMER", wood=3000, gold=3000, ages=2)
    elephant = train.stats(g, "BATTLE_ELEPHANT")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "TUSK_SWORDS")
    train.tick(g, 40)
    assert "TUSK_SWORDS" in g.techs
    assert train.stats(g, "BATTLE_ELEPHANT").attack == elephant.attack + 3
    assert train.stats(g, "KNIGHT").attack == knight.attack     # not a battle elephant
