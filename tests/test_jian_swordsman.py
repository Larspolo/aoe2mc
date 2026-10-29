"""Jian Swordsman (#2134): the barracks of the Wu trains the Jian Swordsman from the Castle Age, with the values of the
AoE2 DE wiki infobox "Jian Swordsman" (the shielded form). It has no elite upgrade. The switch to the unshielded form is
not here."""
from menu_line import item
from test_castle_upgrades import BARRACKS, setup
from test_forging import menus

from game import train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def barracks(civ="WU", ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", BARRACKS)
    return server, g


def test_a_wu_player_trains_it_in_the_castle_age():
    server, _ = barracks(ages=("FEUDAL_AGE",))
    assert item(menus(server)[-1], "Jian Swordsman").endswith(" · Needs the Castle Age")
    server, g = barracks()
    assert item(menus(server)[-1], "Jian Swordsman").endswith(" · queue 0/15")
    assert train.queue(g, "Steve", BARRACKS, "JIAN_SWORDSMAN")


def test_other_civilizations_do_not_see_it():
    for civ in ("SHU", "FRANKS"):
        server, g = barracks(civ)
        assert "Jian Swordsman" not in menus(server)[-1]
        assert train.queue(g, "Steve", BARRACKS, "JIAN_SWORDSMAN") is None
