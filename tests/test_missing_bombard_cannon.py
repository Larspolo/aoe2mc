"""game/civs.py MISSING: a civilization without the bombard cannon (the availability chart of the AoE2 wiki, page
"Bombard_Cannon") does not see it in the menu of its siege workshop, and cannot queue it (#1443)."""
import pytest
from menu_line import item
from test_bombard_cannon import setup
from test_loom import menus

import buildings
from game import train

WITHOUT = sorted(train.civs.MISSING["BOMBARD_CANNON"])
WITH = sorted(set(buildings.CIV_TO_ARCH) - set(WITHOUT))


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


@pytest.mark.parametrize("civ", WITHOUT[:4])
def test_a_civilization_without_it_does_not_see_it(civ):
    server, g, text = menu(civ)
    assert "Bombard Cannon" not in text and "Mangonel" in text
    assert not train.queue(g, "Steve", (3, 3), "BOMBARD_CANNON") and g.stock["wood"] == 1000


@pytest.mark.parametrize("civ", WITH[:2])
def test_a_civilization_with_it_sees_it(civ):
    server, g, text = menu(civ)
    assert item(text, "Bombard Cannon").startswith(f"{train.SLOTS['BOMBARD_CANNON']}:")
    assert item(text, "Bombard Cannon").endswith("queue 0/15")
