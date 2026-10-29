"""game/civs.py MISSING: a civilization without the hand cannoneer (the availability chart of the AoE2 wiki, page
"Hand_Cannoneer") does not see it in the menu of its archery range, and cannot queue it (#1535). "-" in the chart means
"no Ring Archer Armor", not "no unit"."""
import pytest
from menu_line import item
from test_hand_cannoneer import setup
from test_loom import menus

import buildings
from game import train

WITHOUT = sorted(train.civs.MISSING["HAND_CANNONEER"])
WITH = sorted(set(buildings.CIV_TO_ARCH) - set(WITHOUT))


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


@pytest.mark.parametrize("civ", WITHOUT[:4])
def test_a_civilization_without_it_does_not_see_it(civ):
    server, g, text = menu(civ)
    assert "Hand Cannoneer" not in text and "Archer" in text
    assert not train.queue(g, "Steve", (3, 3), "HAND_CANNONEER") and g.stock["food"] == 1000


@pytest.mark.parametrize("civ", WITH[:3])
def test_a_civilization_with_it_sees_it(civ):
    server, g, text = menu(civ)
    assert item(text, "Hand Cannoneer").startswith(f"{train.SLOTS['HAND_CANNONEER']}:")
    assert item(text, "Hand Cannoneer").endswith("queue 0/15")
