"""game/civs.py MISSING: a civilization without the hand cannoneer in the availability chart of the AoE2 wiki
(MediaWiki API, page "Hand_Cannoneer", 2026-10-27: Default = 0) does not see it in the menu of its archery range, and
cannot queue it (#1535). "-" in the chart means "no Ring Archer Armor", not "no unit"."""
import pytest
from test_hand_cannoneer import setup
from test_loom import menus

import buildings
from game import civs, train

HAVE = {"BERBERS", "BOHEMIANS", "BURGUNDIANS", "BYZANTINES", "DRAVIDIANS", "FRANKS", "GEORGIANS", "GOTHS", "GURJARAS",
        "HINDUSTANIS", "ITALIANS", "JAPANESE", "KHMER", "KOREANS", "LITHUANIANS", "MALIANS", "PERSIANS", "PORTUGUESE",
        "SARACENS", "SPANISH", "TATARS", "TEUTONS", "TURKS"}   # the chart rows not 0


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_list_is_the_civilizations_without_the_chart_entry():
    assert set(civs.MISSING["HAND_CANNONEER"]) == set(buildings.CIV_TO_ARCH) - HAVE


@pytest.mark.parametrize("civ", ["BRITONS", "MONGOLS", "AZTECS", "VIETNAMESE"])
def test_a_civilization_without_it_does_not_see_it(civ):
    server, g, text = menu(civ)
    assert "Hand Cannoneer" not in text and "Archer" in text
    assert not train.queue(g, "Steve", (3, 3), "HAND_CANNONEER") and g.stock["food"] == 1000


@pytest.mark.parametrize("civ", ["TURKS", "FRANKS", "GURJARAS"])
def test_a_civilization_with_it_sees_it(civ):
    server, g, text = menu(civ)
    assert " 7:pillager_spawn_egg:Hand Cannoneer:45 food · 50 gold · 34 s · queue 0/15" in text
