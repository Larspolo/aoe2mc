"""A sea gate is as high as its sea wall and has the same cap (#3104)."""
import numpy as np
import pytest

import aoe2mc
import buildings

T = 4
PLAYERS = {1: {"color": "blue", "arch": "western"}}


def obj(n, x, y):
    return dict(kind="B", name=n, player=1, x=x, y=y, rotation=0.0, hero=False, garrisoned=False)


def tops(objs, at):
    """The top block (y, state) of each object in the block column at[i], drawn in a line with the others."""
    walls, gates = buildings.plan_walls(objs)
    out = []
    for o, (cx, cz) in zip(objs, at):
        cols = aoe2mc.Columns(24, np.zeros((24, 24), np.int16), np.zeros((24, 24), np.float32),
                              {0: "GRASS_1"}, T, 3, np.random.default_rng(1))
        E = aoe2mc.Edits(cols)
        buildings.place_building(E, cols, aoe2mc.B, o, PLAYERS, walls, gates)
        x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
        y = np.where(~np.isin(ids, [aoe2mc.B("air"), aoe2mc.B("barrier")]) & (x == cx) & (z == cz), y, -1)
        out.append((int(y.max()), aoe2mc.B.states[ids[y.argmax()]].split("[")[0]))
    return out


@pytest.mark.parametrize("wall,gate", [("SEA_WALL", "SEA_GATE_SOUTHWEST_TO_NORTHEAST"),
                                       ("STONE_WALL", "GATE_SOUTHWEST_TO_NORTHEAST"),
                                       ("FORTIFIED_WALL", "FORTIFIED_GATE_SOUTHWEST_TO_NORTHEAST")])
def test_gate_has_the_height_of_its_wall(wall, gate):
    objs = [obj(wall, x + 0.5, 10.5) for x in (5, 6, 7, 13, 14)] + [obj(gate, 10.0, 10.5)]
    t = tops(objs, [(x * T, 41) for x in (5, 6, 7, 13, 14)] + [(32, 41)])   # the walls, a gate tower
    assert t[-1] == t[0]


def test_diagonal_sea_gate_is_as_high_as_a_fortified_gate():
    at = [(37, 37)]                                      # a tower on an end tile
    assert tops([obj("SEA_GATE_WEST_TO_EAST", 10.5, 10.5)], at)[0][0] == \
        tops([obj("FORTIFIED_GATE_WEST_TO_EAST", 10.5, 10.5)], at)[0][0] > \
        tops([obj("GATE_WEST_TO_EAST", 10.5, 10.5)], at)[0][0]


def test_fortified_names():
    assert all(map(buildings.fortified, ("SEA_WALL", "SEA_GATE", "CITY_WALL", "FORTIFIED_GATE", "FORT_WALL")))
    assert not any(map(buildings.fortified, ("STONE_WALL", "GATE", "PALISADE_WALL")))
