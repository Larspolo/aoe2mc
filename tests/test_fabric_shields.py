"""Fabric Shields (#2047): the castle of the Incas researches it in the Imperial Age (slot 7: 600 food, 600 gold,
40 s), with the values of the AoE2 DE wiki ("Fabric Shields"). The kamayuks and the slingers get +1 melee and +1
pierce armor. Only the Incas have it (the key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.CIV_TECHS["FABRIC_SHIELDS"] == "INCAS"
    assert len(train.HELP["FABRIC_SHIELDS"]) <= 50 and "INCAS" not in train.civs.MISSING["FABRIC_SHIELDS"]
    assert "BRITONS" in train.civs.MISSING["FABRIC_SHIELDS"]


def test_only_the_castle_of_the_incas_researches_it():
    server, g = setup("INCAS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Fabric Shields:600 food · 600 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Fabric Shields" not in menus(server)[-1]


def test_the_effect_changes_the_live_and_the_new_units():
    server, g = setup("INCAS", food=2000, wood=0, gold=2000, ages=3)
    before = train.stats(g, "SLINGER")
    assert train.queue(g, "Steve", CASTLE, "FABRIC_SHIELDS")
    train.tick(g, 40)
    assert "FABRIC_SHIELDS" in g.techs
    after = train.stats(g, "SLINGER")
    assert after.melee == before.melee + 1 and after.pierce == before.pierce + 1
    assert train.stats(g, "KAMAYUK").melee == combat.stats("KAMAYUK").melee + 1
    assert train.stats(g, "ARBALESTER").melee == combat.stats("ARBALESTER").melee   # not a kamayuk or slinger
