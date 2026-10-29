"""Xianbei Raider (#2160): the archery range of the own civilization (game/data/civs.jsonl) trains the Xianbei Raider from
the Castle Age, with the values of game/data/train.jsonl. It has no elite upgrade. The hit points are the base value:
the civilization bonus of each age changes them."""
from test_castle_upgrades import RANGE, setup
from test_forging import menus
from test_urumi_swordsman import item

from game import civs, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
ALL = {r["name"] for r in civs.ROWS}
OWN = sorted(ALL - set(civs.MISSING["XIANBEI_RAIDER"]))[0]
OTHERS = sorted(civs.MISSING["XIANBEI_RAIDER"])[:2]


def archery_range(civ=OWN, ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


def test_the_menu_has_the_unit_from_the_castle_age_for_the_own_civ():
    slot, kind, name = train.ITEMS["XIANBEI_RAIDER"]
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert f" {slot}:gray_dye:{name}:" in menus(server)[-1] and "Needs the Castle Age" in menus(server)[-1]
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    assert item(g, "XIANBEI_RAIDER", f"queue 0/{train.QUEUE}") in menus(server)[-1] + " "
    assert train.queue(g, "Steve", RANGE, "XIANBEI_RAIDER")
    for civ in OTHERS:
        server, g = archery_range(civ)
        train.open_menu(g, "Steve", RANGE)
        assert f":{name}:" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", RANGE, "XIANBEI_RAIDER") is None, civ
