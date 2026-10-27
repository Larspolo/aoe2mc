"""game/civs.py MISSING: a civilization without the bombard cannon in the availability chart of the AoE2 wiki
(MediaWiki API, page "Bombard_Cannon", 2026-10-27: Default = 0, Khmer = -1: no longer) does not see it in the menu of its
siege workshop, and cannot queue it (#1443)."""
import pytest
from test_bombard_cannon import setup
from test_loom import menus

import buildings
from game import civs, train

HAVE = {"BERBERS", "BOHEMIANS", "BURGUNDIANS", "BURMESE", "BYZANTINES", "DRAVIDIANS", "ETHIOPIANS", "FRANKS", "GOTHS",
        "GURJARAS", "HINDUSTANIS", "ITALIANS", "JURCHENS", "KOREANS", "LITHUANIANS", "MALAY", "MALIANS", "PERSIANS",
        "POLES", "PORTUGUESE", "SARACENS", "SPANISH", "TEUTONS", "TURKS", "VIETNAMESE"}   # the chart rows not 0 or -1


def menu(civ):
    server, g = setup(techs=["CHEMISTRY"])
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_the_list_is_the_civilizations_without_the_chart_entry():
    assert set(civs.MISSING["BOMBARD_CANNON"]) == set(buildings.CIV_TO_ARCH) - HAVE


@pytest.mark.parametrize("civ", ["KHMER", "BRITONS", "MONGOLS", "AZTECS"])
def test_a_civilization_without_it_does_not_see_it(civ):
    server, g, text = menu(civ)
    assert "Bombard Cannon" not in text and "Mangonel" in text
    assert not train.queue(g, "Steve", (3, 3), "BOMBARD_CANNON") and g.stock["wood"] == 1000


def test_the_turks_see_it():
    server, g, text = menu("TURKS")
    assert "7:tnt_minecart:Bombard Cannon:225 wood · 225 gold · 56 s · queue 0/15" in text
