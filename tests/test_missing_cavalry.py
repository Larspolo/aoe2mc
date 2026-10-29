"""game/civs.py MISSING: the stable has no knight and the archery range no cavalry archer for the civilizations that do
not have them in AoE2 DE (AoE2 wiki "Knight (Age of Empires II)" and "Cavalry Archer (Age of Empires II)", the
availability chart: "= 0", or not in the chart when its default is 0), #1430."""
import pytest
from test_train_knight import menu, setup

import buildings
from game import train

UNITS = [("STABLE", "KNIGHT", "Knight"), ("ARCHERY_RANGE", "CAVALRY_ARCHER", "Cavalry Archer")]


def player(building, civ):
    server, g = setup(building)
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (11, 3))
    return server, g


@pytest.mark.parametrize("building, name, label", UNITS)
def test_no_unit_in_the_menu_of_each_civilization_without_it(building, name, label):
    assert train.civs.MISSING[name]
    for c in sorted(train.civs.MISSING[name]):
        server, g = player(building, c)
        assert f":{label}:" not in menu(server), c
        assert train.queue(g, "Steve", (11, 3), name) is None and g.stock["gold"] == 1000, c


@pytest.mark.parametrize("building, name, label", UNITS)
def test_a_civilization_with_the_unit_has_it_in_the_menu(building, name, label):
    civ = min(set(buildings.CIV_TO_ARCH) - set(train.civs.MISSING[name]))
    server, g = player(building, civ)
    assert f":{label}:" in menu(server)
    assert train.queue(g, "Steve", (11, 3), name)
