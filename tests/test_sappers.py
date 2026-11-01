"""Sappers (#1580): the castle researches it in the Imperial Age (AoE2 wiki "Sappers"), and then the villagers of the
player get more attack against buildings and stone defenses (the class "building" of combat: also the walls) and
against rams. Other units do not change."""
import lang
from test_arson import hit
from test_hoardings import setup

from game import combat, train


def test_the_castle_menu_shows_it_in_the_imperial_age_after_hoardings():
    from test_loom import menus
    for age, shown in ((2, False), (3, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (12, 4))
        assert (":book:Sappers:" in menus(server)[-1]) == shown


def test_the_research_gives_villagers_attack_against_buildings_walls_and_rams():
    server, g = setup()
    before, cost, t = dict(g.stock), train.price(g, "SAPPERS"), train.seconds(g, "SAPPERS")
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (12, 4)), train.ITEMS["SAPPERS"][0]) == 1
    assert g.stock == {k: v - cost.get(k, 0) for k, v in before.items()}
    train.tick(g, t - 1)
    assert "SAPPERS" not in g.techs
    train.tick(g, 1)
    assert "SAPPERS" in g.techs and "Sappers is researched." in " ".join(map(lang.english, server.log))
    for name in ("VILLAGER_MALE", "VILLAGER_FEMALE_FARMER"):
        old, new = combat.stats(name), train.stats(g, name)
        assert hit(new, combat.stats("HOUSE")) > hit(old, combat.stats("HOUSE"))
        assert hit(new, combat.wall("STONE_WALL", 3)) > hit(old, combat.wall("STONE_WALL", 3))   # also walls (#1590)
        assert hit(new, combat.stats("BATTERING_RAM")) > hit(old, combat.stats("BATTERING_RAM"))
        assert hit(new, combat.stats("MILITIA")) == hit(old, combat.stats("MILITIA"))
    for name in ("MILITIA", "BATTERING_RAM", "MONK"):
        assert train.stats(g, name) == combat.stats(name), name
