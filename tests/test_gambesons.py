"""game/train.py: the barracks researches Gambesons (#1420, AoE2 DE wiki "Gambesons (Age of Empires II)"): Castle Age,
50 food, 100 gold, 25 s, the militia line +1 pierce armor; not for the civilizations without it (civs.MISSING)."""
from test_forging import menus, setup

from game import civs, combat, train

BARRACKS = (17, 3)


def castle(civ=None):
    server, g = setup(food=100)
    g.techs.add("CASTLE_AGE")
    g.stock.update(gold=100)
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_barracks_menu_has_gambesons_from_the_castle_age():
    assert train.TECH_AGE["GAMBESONS"] == 2
    server, g = setup(food=100)                                    # the Feudal Age: not yet
    g.stock.update(gold=100)
    train.open_menu(g, "Steve", BARRACKS)
    assert "Gambesons" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "GAMBESONS") is None
    server, g = castle()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 4:book:Gambesons:50 food · 100 gold · 25 s · research " in menus(server)[-1] + " "


def test_the_research_gives_the_militia_line_one_pierce_armor():
    server, g = castle()
    old = {n: train.stats(g, n) for n in ("MILITIA", "LONG_SWORDSMAN", "CHAMPION", "SPEARMAN", "ARCHER")}
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.order(g, "Steve", rect, 4) == 1
    train.tick(g, 25)
    assert "GAMBESONS" in g.techs and g.stock["food"] == 50 and g.stock["gold"] == 0
    for n in ("MILITIA", "LONG_SWORDSMAN", "CHAMPION"):
        assert train.stats(g, n) == old[n]._replace(pierce=old[n].pierce + 1)
    assert train.stats(g, "SPEARMAN") == old["SPEARMAN"] and train.stats(g, "ARCHER") == old["ARCHER"]
    assert train.stats(g, "VILLAGER_MALE") == combat.stats("VILLAGER_MALE")
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live militia gets the new armor


def test_not_for_the_civilizations_without_it():
    assert {"GOTHS", "VIKINGS", "CHINESE"} <= set(civs.MISSING["GAMBESONS"])
    assert not {"BRITONS", "TEUTONS", "JAPANESE"} & set(civs.MISSING["GAMBESONS"])
    server, g = castle("GOTHS")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Gambesons" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "GAMBESONS") is None
    server, g = castle("BRITONS")
    train.open_menu(g, "Steve", BARRACKS)
    assert ":book:Gambesons:" in menus(server)[-1]
