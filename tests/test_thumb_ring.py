"""game/train.py: the archery range researches Thumb Ring (#1421, AoE2 DE wiki "Thumb Ring"): Castle Age, the
archers fire faster; not the skirmishers and the gunpowder units; not for
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
    assert train.ITEMS["THUMB_RING"][2] not in menus(server)[-1]
    assert train.queue(g, "Steve", RANGE, "THUMB_RING") is None
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert f":{train.ITEMS['THUMB_RING'][2]}:" in menus(server)[-1]


def test_the_archers_fire_faster_after_the_research():
    server, g = player()
    names = ("ARCHER", "CROSSBOWMAN", "CAVALRY_ARCHER", "SKIRMISHER", "HAND_CANNONEER", "MILITIA")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", RANGE)
    assert train.order(g, "Steve", rect, train.layout(g, rect)["THUMB_RING"][0]) == 1
    train.tick(g, train.TRAIN_TIMES["THUMB_RING"])
    assert "THUMB_RING" in g.techs
    for n in ("ARCHER", "CROSSBOWMAN", "CAVALRY_ARCHER"):
        new = train.stats(g, n)
        assert new.reload < old[n].reload and new == old[n]._replace(reload=new.reload), n
    for n in ("SKIRMISHER", "HAND_CANNONEER", "MILITIA"):
        assert train.stats(g, n) == old[n]
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live archer gets the new reload time


def test_not_for_the_civilizations_without_it():
    label, without = train.ITEMS["THUMB_RING"][2], set(civs.MISSING["THUMB_RING"])
    server, g = player(min(without))
    train.open_menu(g, "Steve", RANGE)
    assert label not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "THUMB_RING") is None
    server, g = player(min(r["name"] for r in civs.ROWS if r["name"] not in without))
    train.open_menu(g, "Steve", RANGE)
    assert f":{label}:" in menus(server)[-1]
