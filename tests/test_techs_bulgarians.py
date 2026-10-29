"""The unique technologies of the Bulgarians (#4098): Stirrups (Castle Age, 400 food, 200 gold, 35 s: the cavalry
reloads 33 % faster) and Bagains (Imperial Age, 900 food, 450 gold, 40 s: +5 melee armor of the Two-Handed Swordsman
line). The values are those of the AoE2 DE wiki ("Unique technology"). Only the Bulgarians have them."""
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["STIRRUPS"]) <= 50 and "BULGARIANS" not in train.civs.MISSING["STIRRUPS"]
    assert "BRITONS" in train.civs.MISSING["STIRRUPS"]
    assert len(train.HELP["BAGAINS"]) <= 50 and "BULGARIANS" not in train.civs.MISSING["BAGAINS"]
    assert "BRITONS" in train.civs.MISSING["BAGAINS"]


def test_only_the_castle_of_the_bulgarians_researches_stirrups():
    server, g = setup("BULGARIANS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert " 6:book:Stirrups:400 food · 200 gold · 35 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Stirrups" not in menus(server)[-1]


def test_only_the_castle_of_the_bulgarians_researches_bagains():
    server, g = setup("BULGARIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert " 7:book:Bagains:900 food · 450 gold · 40 s · research " in menus(server)[-1] + " "
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert "Bagains" not in menus(server)[-1]


def test_stirrups_reload_cavalry_33_percent_faster_and_keep_infantry():
    server, g = setup("BULGARIANS", food=3000, wood=0, gold=3000, ages=2)
    knight = train.stats(g, "KNIGHT")
    militia = train.stats(g, "MILITIA")
    assert train.queue(g, "Steve", CASTLE, "STIRRUPS")
    train.tick(g, 35)
    assert "STIRRUPS" in g.techs
    assert train.stats(g, "KNIGHT").reload == knight.reload * 0.75     # 2.0 → 1.5, not rounded to 2
    assert train.stats(g, "MILITIA").reload == militia.reload          # not cavalry


def test_bagains_add_melee_armor_to_the_two_handed_swordsmen_only():
    server, g = setup("BULGARIANS", food=3000, wood=0, gold=3000, ages=3)
    champion = train.stats(g, "CHAMPION")
    man_at_arms = train.stats(g, "MAN_AT_ARMS")
    assert train.queue(g, "Steve", CASTLE, "BAGAINS")
    train.tick(g, 40)
    assert "BAGAINS" in g.techs
    assert train.stats(g, "CHAMPION").melee == champion.melee + 5
    assert train.stats(g, "MAN_AT_ARMS").melee == man_at_arms.melee    # not a Two-Handed Swordsman
