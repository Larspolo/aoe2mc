"""Unique technologies (#2021): the castle of the Vikings researches Chieftains in the Castle Age (slot 6: 600 food,
450 gold, 40 s) and Bogsveigar in the Imperial Age (slot 7: 650 food, 500 gold, 40 s), with the values of the AoE2 DE
wiki ("Chieftains", "Bogsveigar"). Only the Vikings have them (the key "civ" of data/train.jsonl)."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["civ"] == {"CHIEFTAINS": "VIKINGS", "BOGSVEIGAR": "VIKINGS"} | {
        n: c for n, c in train.BY_KEY["civ"].items() if n not in ("CHIEFTAINS", "BOGSVEIGAR")}
    for name in ("CHIEFTAINS", "BOGSVEIGAR"):
        assert len(train.HELP[name]) <= 50 and "VIKINGS" not in train.civs.MISSING[name]
        assert "BRITONS" in train.civs.MISSING[name]


def test_only_the_castle_of_the_vikings_researches_them():
    server, g = setup("VIKINGS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert " 6:book:Chieftains:600 food · 450 gold · 40 s · research " in menu
    assert "Bogsveigar" not in menu                                    # the Imperial Age
    server, g = setup("VIKINGS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Bogsveigar:650 food · 500 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Chieftains" not in menus(server)[-1] and "Bogsveigar" not in menus(server)[-1]


def test_the_effects_change_the_live_and_the_new_units():
    server, g = setup("VIKINGS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["bk"] = "BERSERK"
    g.game.entities.setdefault("bk", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    before = train.stats(g, "BERSERK")
    assert train.queue(g, "Steve", CASTLE, "CHIEFTAINS")
    train.tick(g, 40)
    assert "CHIEFTAINS" in g.techs
    after = train.stats(g, "BERSERK")
    assert after.bonus["cavalry"] == before.bonus.get("cavalry", 0) + 5 and after.bonus["camel"] == before.bonus.get("camel", 0) + 4
    assert train.stats(g, "ARBALESTER").bonus == combat.stats("ARBALESTER").bonus   # not infantry
    assert combat.stats_command("bk", "BERSERK", after) in server.log      # the live berserk
    arb = train.stats(g, "ARBALESTER").attack
    assert train.queue(g, "Steve", CASTLE, "BOGSVEIGAR")
    train.tick(g, 40)
    assert train.stats(g, "ARBALESTER").attack == arb + 1 and train.stats(g, "BERSERK").attack == after.attack
