"""game/civs.py MISSING: the stable has no knight and the archery range no cavalry archer for the civilizations that do
not have them in AoE2 DE (AoE2 wiki "Knight (Age of Empires II)" and "Cavalry Archer (Age of Empires II)", the
availability chart: "= 0", or not in the chart when its default is 0), #1430."""
import pytest
from test_train_knight import menu, setup

from game import civs, train

KNIGHT = {"AZTECS", "BENGALIS", "DRAVIDIANS", "GURJARAS", "HINDUSTANIS", "INCAS", "JURCHENS", "KHITANS", "MAPUCHE",
          "MAYANS", "MUISCA", "SHU", "TUPI", "WEI", "WU"}
CAVALRY_ARCHER = {"AZTECS", "BENGALIS", "BOHEMIANS", "BRITONS", "BURGUNDIANS", "CELTS", "DANES", "DRAVIDIANS", "FRANKS",
                  "GURJARAS", "INCAS", "ITALIANS", "MAPUCHE", "MAYANS", "MUISCA", "POLES", "PORTUGUESE", "SAXONS",
                  "SICILIANS", "SPANISH", "TEUTONS", "TUPI", "VARANGIANS", "VIKINGS", "WEI"}
UNITS = [("STABLE", "KNIGHT", "Knight", KNIGHT, "FRANKS"), ("ARCHERY_RANGE", "CAVALRY_ARCHER", "Cavalry Archer",
                                                             CAVALRY_ARCHER, "MONGOLS")]


def player(building, civ):
    server, g = setup(building)
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (11, 3))
    return server, g


def test_the_lists_are_the_availability_charts_of_the_wiki():
    assert set(civs.MISSING["KNIGHT"]) == KNIGHT and len(civs.MISSING["KNIGHT"]) == len(KNIGHT)
    assert set(civs.MISSING["CAVALRY_ARCHER"]) == CAVALRY_ARCHER and len(civs.MISSING["CAVALRY_ARCHER"]) == len(CAVALRY_ARCHER)


@pytest.mark.parametrize("building, name, label, missing, civ", UNITS)
def test_no_unit_in_the_menu_of_each_civilization_without_it(building, name, label, missing, civ):
    for c in sorted(missing):
        server, g = player(building, c)
        assert f":{label}:" not in menu(server), c
        assert train.queue(g, "Steve", (11, 3), name) is None and g.stock["gold"] == 1000, c


@pytest.mark.parametrize("building, name, label, missing, civ", UNITS)
def test_a_civilization_with_the_unit_has_it_in_the_menu(building, name, label, missing, civ):
    server, g = player(building, civ)
    assert f":{label}:" in menu(server)
    assert train.queue(g, "Steve", (11, 3), name)
