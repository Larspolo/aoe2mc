"""Hauberk (#4110): the castle of the Sicilians researches it in the Imperial Age (slot 7: 700 food, 600 gold, 45 s),
with the values of the AoE2 DE wiki ("Unique technology"). Only the Sicilians have it (the key "civ" of data/train.jsonl).
Its effect: knights +1 melee and +2 pierce armor, not the scout cavalry."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["HAUBERK"]) <= 50 and "SICILIANS" not in train.civs.MISSING["HAUBERK"]
    assert "BRITONS" in train.civs.MISSING["HAUBERK"]


def test_only_the_castle_of_the_sicilians_researches_it():
    server, g = setup("SICILIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Hauberk:700 food · 600 gold · 45 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Hauberk" not in menus(server)[-1]


def test_the_effect_adds_armor_to_knights_only():
    server, g = setup("SICILIANS", food=3000, wood=0, gold=3000, ages=3)
    cavalier = train.stats(g, "CAVALIER")
    scout = train.stats(g, "SCOUT_CAVALRY")
    assert train.queue(g, "Steve", CASTLE, "HAUBERK")
    train.tick(g, 45)
    assert "HAUBERK" in g.techs
    assert train.stats(g, "CAVALIER").pierce == cavalier.pierce + 2
    assert train.stats(g, "CAVALIER").melee == cavalier.melee + 1
    assert train.stats(g, "SCOUT_CAVALRY").pierce == scout.pierce     # not a knight
