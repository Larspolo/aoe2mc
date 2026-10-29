"""game/train.py: the barracks researches Gambesons (#1420) from the Castle Age: the militia line gets more pierce armor;
not for the civilizations without it (civs.MISSING)."""
from test_forging import entry, menus, setup

from game import civs, combat, train

BARRACKS = (17, 3)
WITHOUT = sorted(civs.MISSING["GAMBESONS"])[0]
WITH = next(c["name"] for c in sorted(civs.ROWS, key=lambda c: c["name"]) if c["name"] not in civs.MISSING["GAMBESONS"])


def castle(civ=None):
    server, g = setup(food=100)
    g.techs.add("CASTLE_AGE")
    g.stock.update(gold=100)
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_barracks_menu_has_gambesons_from_the_castle_age():
    server, g = setup(food=100)                                    # the Feudal Age: not yet
    g.stock.update(gold=100)
    train.open_menu(g, "Steve", BARRACKS)
    assert "Gambesons" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "GAMBESONS") is None
    server, g = castle()
    train.open_menu(g, "Steve", BARRACKS)
    assert f" {entry(g, 'GAMBESONS', 'research')} " in menus(server)[-1] + " "


def test_the_research_gives_the_militia_line_more_pierce_armor():
    server, g = castle()
    old = {n: train.stats(g, n) for n in ("MILITIA", "LONG_SWORDSMAN", "CHAMPION", "SPEARMAN", "ARCHER")}
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.order(g, "Steve", rect, train.ITEMS["GAMBESONS"][0]) == 1
    train.tick(g, train.TRAIN_TIMES["GAMBESONS"])
    cost = train.COSTS["GAMBESONS"]
    assert "GAMBESONS" in g.techs and g.stock["food"] == 100 - cost.get("food", 0) and g.stock["gold"] == 100 - cost.get("gold", 0)
    for n in ("MILITIA", "LONG_SWORDSMAN", "CHAMPION"):
        new = train.stats(g, n)
        assert new.pierce > old[n].pierce and new == old[n]._replace(pierce=new.pierce)
    assert train.stats(g, "SPEARMAN") == old["SPEARMAN"] and train.stats(g, "ARCHER") == old["ARCHER"]
    assert train.stats(g, "VILLAGER_MALE") == combat.stats("VILLAGER_MALE")
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live militia gets the new armor


def test_not_for_the_civilizations_without_it():
    server, g = castle(WITHOUT)
    train.open_menu(g, "Steve", BARRACKS)
    assert "Gambesons" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "GAMBESONS") is None
    server, g = castle(WITH)
    train.open_menu(g, "Steve", BARRACKS)
    assert ":book:Gambesons:" in menus(server)[-1]
