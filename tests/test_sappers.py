"""Sappers (#1580): the castle researches it in the Imperial Age (400 food, 200 wood, 10 s; AoE2 wiki "Sappers"), and
then the villagers of the player get +15 attack against buildings and stone defenses (the class "building" of
combat: also the walls) and +3 against rams. Other units do not change."""
from test_arson import hit
from test_hoardings import setup

from game import civs, combat, train


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["SAPPERS"]) <= 50 and "SAPPERS" in train.TRAINS["CASTLE"]
    assert len(civs.MISSING["SAPPERS"]) == 19 and {"FRANKS", "JAPANESE", "WU"} <= set(civs.MISSING["SAPPERS"])
    assert "BRITONS" not in civs.MISSING["SAPPERS"]                     # the wiki availability chart


def test_the_castle_menu_shows_it_in_the_imperial_age_after_hoardings():
    from test_loom import menus
    for age, shown in ((2, False), (3, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (12, 4))
        assert (":book:Sappers:" in menus(server)[-1]) == shown
    assert " 4:book:Sappers:400 food · 200 wood · 10 s" in menus(server)[-1]


def test_the_research_gives_villagers_attack_against_buildings_walls_and_rams():
    server, g = setup()
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (12, 4)), train.ITEMS["SAPPERS"][0]) == 1
    assert g.stock["food"] == 0 and g.stock["wood"] == 200
    train.tick(g, 9)
    assert "SAPPERS" not in g.techs
    train.tick(g, 1)
    assert "SAPPERS" in g.techs and "Sappers is researched." in " ".join(server.log)
    for name in ("VILLAGER_MALE", "VILLAGER_FEMALE_FARMER"):
        old, new = combat.stats(name), train.stats(g, name)
        assert hit(new, combat.stats("HOUSE")) == hit(old, combat.stats("HOUSE")) + 15
        assert hit(old, combat.wall("STONE_WALL", 3)) == 9 and hit(new, combat.wall("STONE_WALL", 3)) == 24   # +3 +6 (#1590)
        assert hit(new, combat.stats("BATTERING_RAM")) == hit(old, combat.stats("BATTERING_RAM")) + 3
        assert hit(new, combat.stats("MILITIA")) == hit(old, combat.stats("MILITIA"))
    for name in ("MILITIA", "BATTERING_RAM", "MONK"):
        assert train.stats(g, name) == combat.stats(name), name
