"""Howdah (#4104): the castle of the Burmese researches it in the Imperial Age (slot 7: 400 food, 300 wood, 40 s),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Burmese have it (the key "civ" of data/train.jsonl).
Its effect: battle elephants +1 melee and +1 pierce armor."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["HOWDAH"]) <= 50 and "BURMESE" not in train.civs.MISSING["HOWDAH"]
    assert "BRITONS" in train.civs.MISSING["HOWDAH"]


def test_only_the_castle_of_the_burmese_researches_it():
    server, g = setup("BURMESE", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Howdah:400 food · 300 wood · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Howdah" not in menus(server)[-1]


def test_the_effect_adds_armor_to_battle_elephants_only():
    server, g = setup("BURMESE", food=3000, wood=3000, ages=3)
    elephant = train.stats(g, "ELITE_BATTLE_ELEPHANT")
    knight = train.stats(g, "KNIGHT")
    assert train.queue(g, "Steve", CASTLE, "HOWDAH")
    train.tick(g, 40)
    assert "HOWDAH" in g.techs
    assert train.stats(g, "ELITE_BATTLE_ELEPHANT").pierce == elephant.pierce + 1
    assert train.stats(g, "KNIGHT").pierce == knight.pierce     # not a battle elephant
