"""Chatras (#4113): the castle of the Vietnamese researches it in the Castle Age (slot 6: 250 food, 250 gold, 40 s),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Vietnamese have it (the key "civ" of
data/train.jsonl). Its effect: Battle Elephants +100 HP."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["CHATRAS"]) <= 50 and "VIETNAMESE" not in train.civs.MISSING["CHATRAS"]
    assert "BRITONS" in train.civs.MISSING["CHATRAS"]


def test_only_the_castle_of_the_vietnamese_researches_it():
    server, g = setup("VIETNAMESE", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Chatras:250 food · 250 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Chatras" not in menus(server)[-1]


def test_the_effect_adds_hp_to_battle_elephants_only():
    server, g = setup("VIETNAMESE", food=3000, wood=0, gold=3000, ages=2)
    elephant = train.stats(g, "BATTLE_ELEPHANT")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "CHATRAS")
    train.tick(g, 40)
    assert "CHATRAS" in g.techs
    assert train.stats(g, "BATTLE_ELEPHANT").hp == elephant.hp + 100
    assert train.stats(g, "KNIGHT").hp == knight.hp     # not a battle elephant
