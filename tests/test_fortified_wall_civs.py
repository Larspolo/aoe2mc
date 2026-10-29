"""game/civs.py MISSING: the university menu has no Fortified Wall for the civilizations that do not have it in AoE2 DE
(the key "not_civs" of its line in game/data/train.jsonl, #1373)."""
import pytest
from test_fortified_wall import COST, entry, setup
from test_loom import menus

from game import civs, train

WITHOUT = sorted(civs.MISSING["FORTIFIED_WALL"])
WITH = next(c["name"] for c in sorted(civs.ROWS, key=lambda c: c["name"]) if c["name"] not in WITHOUT)


def player(civ):
    server, g = setup()
    g.data["players"]["1"]["civ"] = civ
    return server, g


@pytest.mark.parametrize("civ", WITHOUT[:2])
def test_no_fortified_wall_in_the_menu_and_no_queue(civ):
    server, g = player(civ)
    train.open_menu(g, "Steve", (9, 9))
    assert "Fortified Wall" not in menus(server)[-1]
    assert train.queue(g, "Steve", (9, 9), "FORTIFIED_WALL") is None and all(g.stock[r] == n for r, n in COST.items())


def test_a_civilization_with_it_has_it():
    server, g = player(WITH)
    train.open_menu(g, "Steve", (9, 9))
    assert entry(g, "FORTIFIED_WALL", "research") in menus(server)[-1]
    assert train.queue(g, "Steve", (9, 9), "FORTIFIED_WALL")
