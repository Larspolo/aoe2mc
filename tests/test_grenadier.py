"""Grenadier (#2159): the Jurchen archery range trains the grenadier from the Castle Age, with the values of the AoE2
DE wiki infobox "Grenadier" (revision 1090749). Only the Jurchens have it."""
from menu_line import item
from test_castle_upgrades import RANGE, setup
from test_forging import menus

from game import train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def archery_range(civ="JURCHENS", ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


def test_the_menu_has_the_unit_from_the_castle_age_for_the_jurchens():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert item(menus(server)[-1], "Grenadier").endswith(" · Needs the Castle Age")
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    assert item(menus(server)[-1], "Grenadier").endswith(" · queue 0/15")
    g.stock.update(train.price(g, "GRENADIER"))                       # just the cost
    assert train.queue(g, "Steve", RANGE, "GRENADIER") and not any(g.stock[r] for r in train.price(g, "GRENADIER"))
    for civ in ("BRITONS", "CHINESE"):
        server, g = archery_range(civ)
        train.open_menu(g, "Steve", RANGE)
        assert "Grenadier" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", RANGE, "GRENADIER") is None, civ
