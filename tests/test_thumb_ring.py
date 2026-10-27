"""game/train.py: the archery range researches Thumb Ring (#1421, AoE2 DE wiki "Thumb Ring"): Castle Age, 300 food,
250 wood, 45 s, the archers fire 17.65 % faster (reload / 1.1765); not the skirmishers and the gunpowder units; not for
the civilizations without it (civs.MISSING)."""
from test_castle_upgrades import RANGE, setup
from test_forging import menus

from game import civs, train


def player(civ=None, ages=("FEUDAL_AGE", "CASTLE_AGE")):
    server, g = setup(ages=ages, techs=())
    if civ:
        g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_archery_range_menu_has_thumb_ring_from_the_castle_age():
    server, g = player(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert "Thumb Ring" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "THUMB_RING") is None
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert " 5:book:Thumb Ring:300 food · 250 wood · 45 s · research " in menus(server)[-1] + " "


def test_the_archers_fire_faster_after_the_research():
    server, g = player()
    names = ("ARCHER", "CROSSBOWMAN", "CAVALRY_ARCHER", "SKIRMISHER", "HAND_CANNONEER", "MILITIA")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", RANGE)
    assert train.order(g, "Steve", rect, 5) == 1
    train.tick(g, 45)
    assert "THUMB_RING" in g.techs
    for n in ("ARCHER", "CROSSBOWMAN", "CAVALRY_ARCHER"):
        assert train.stats(g, n) == old[n]._replace(reload=round(old[n].reload / 1.1765, 3))
    assert train.stats(g, "ARCHER").reload == 1.7                  # 2 s / 1.1765
    for n in ("SKIRMISHER", "HAND_CANNONEER", "MILITIA"):
        assert train.stats(g, n) == old[n]
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live archer gets the new reload time


def test_not_for_the_civilizations_without_it():
    assert {"BRITONS", "CELTS", "WU"} <= set(civs.MISSING["THUMB_RING"])
    assert not {"MONGOLS", "ETHIOPIANS", "CHINESE"} & set(civs.MISSING["THUMB_RING"])
    server, g = player("BRITONS")
    train.open_menu(g, "Steve", RANGE)
    assert "Thumb Ring" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "THUMB_RING") is None
    server, g = player("MONGOLS")
    train.open_menu(g, "Steve", RANGE)
    assert ":book:Thumb Ring:" in menus(server)[-1]
