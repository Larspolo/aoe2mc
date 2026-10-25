"""Every AoE2 building draws without errors in every architecture set, with valid block states only."""
import numpy as np
import pytest
from AoE2ScenarioParser.datasets.buildings import BuildingInfo

import aoe2mc
import buildings
import mcvalid

T = 4


def flat_columns(size=16):
    return aoe2mc.Columns(size, np.zeros((size, size), np.int16), np.zeros((size, size), np.float32),
                          {0: "GRASS_1"}, T, 3, np.random.default_rng(1))


@pytest.mark.parametrize("arch", sorted(buildings.ARCH))
def test_every_building_in_every_architecture_set(arch):
    players = {1: {"color": "blue", "arch": arch, "civ": "TEST"}}
    for b in BuildingInfo:
        cols = flat_columns()
        E = aoe2mc.Edits(cols)
        o = dict(kind="B", name=b.name, player=1, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False)
        walls, gates = buildings.plan_walls([o])
        buildings.place_building(E, cols, aoe2mc.B, o, players, walls, gates)
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


def test_every_civilization_has_a_known_architecture_set():
    assert set(buildings.CIV_TO_ARCH.values()) <= set(buildings.ARCH)
