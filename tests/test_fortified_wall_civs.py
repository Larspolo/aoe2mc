"""game/civs.py MISSING: the university menu has no Fortified Wall for the civilizations that do not have it in AoE2 DE
(AoE2 wiki "Fortified Wall (Age of Empires II)", availability chart, #1373)."""
import pytest
from test_fortified_wall import setup
from test_loom import menus

from game import civs, train

WIKI = {"BULGARIANS", "CUMANS", "DANES", "GOTHS", "HUNS", "MAGYARS", "MALAY", "MAPUCHE", "MUISCA", "PERSIANS",
        "SICILIANS", "TUPI", "WU"}                                  # "= 0" in the availability chart


def player(civ):
    server, g = setup()
    g.data["players"]["1"]["civ"] = civ
    return server, g


def test_the_list_is_the_availability_chart_of_the_wiki():
    assert set(civs.MISSING["FORTIFIED_WALL"]) == WIKI and len(civs.MISSING["FORTIFIED_WALL"]) == len(WIKI)


@pytest.mark.parametrize("civ", ["GOTHS", "HUNS"])
def test_no_fortified_wall_in_the_menu_and_no_queue(civ):
    server, g = player(civ)
    train.open_menu(g, "Steve", (9, 9))
    assert "Fortified Wall" not in menus(server)[-1]
    assert train.queue(g, "Steve", (9, 9), "FORTIFIED_WALL") is None and g.stock["food"] == 200


def test_a_britons_player_has_it():
    server, g = player("BRITONS")
    train.open_menu(g, "Steve", (9, 9))
    assert "0:book:Fortified Wall:200 food · 100 wood · 50 s · research" in menus(server)[-1]
    assert train.queue(g, "Steve", (9, 9), "FORTIFIED_WALL")
