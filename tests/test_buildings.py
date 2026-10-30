"""Every AoE2 building draws without errors in every architecture set, with valid block states only."""
from collections import Counter

import mcvalid
import numpy as np
import pytest
from AoE2ScenarioParser.datasets.buildings import BuildingInfo

import aoe2mc
import buildings

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


def test_weather_does_not_depend_on_the_order_of_block_ids():
    def weathered(blocks):
        c = buildings.Canvas(blocks, 8, height=8)
        c.box(0, 8, 0, 3, 0, 8, "stone_bricks")
        c.box(0, 8, 3, 6, 0, 8, "spruce_planks")
        c.box(0, 8, 6, 8, 0, 8, "calcite")
        buildings.weather(c)
        return [blocks.states[i] if i >= 0 else None for i in c.a.ravel()]
    other = aoe2mc.Blocks()             # an earlier conversion registered the variants first, in another order
    for s in sorted({v for opts in buildings.TEXTURE.values() for v, _ in opts} | set(buildings.TEXTURE)):
        other(s)
    assert weathered(aoe2mc.Blocks()) == weathered(other)


def gate_solid(name, wall_tiles=()):
    """Solid blocks at head height of a gate at tile (8, 8), as a set of block (x, z), and the gate direction."""
    cols, B = flat_columns(), aoe2mc.B
    E = aoe2mc.Edits(cols)
    obj = lambda n, x, y: dict(kind="B", name=n, player=1, x=x, y=y, rotation=0.0, hero=False, garrisoned=False)
    o = obj(name, 8.5, 8.5)
    walls, gates = buildings.plan_walls([o] + [obj("STONE_WALL", x + 0.5, y + 0.5) for x, y in wall_tiles])
    buildings.place_building(E, cols, B, o, {1: {"color": "blue", "arch": "western"}}, walls, gates)
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    head = (y == int(cols.wtop.max()) + 2) & (ids != B("air"))
    return {(int(a), int(b)) for a, b in zip(x[head], z[head])}, gates[id(o)]


@pytest.mark.parametrize("name", ["GATE_WEST_TO_EAST", "PALISADE_GATE_NORTH_TO_SOUTH", "FORTIFIED_GATE_WEST_TO_EAST"])
def test_diagonal_gates_are_drawn_on_the_diagonal(name):
    """Screen west-east is the tile diagonal (+1, +1), screen north-south is (+1, -1) (#25)."""
    solid, d = gate_solid(name)
    x0 = 28                                              # (8.5 - 1.5) * T
    if d == "diag-":
        solid = {(x, 2 * x0 + 11 - z) for x, z in solid}  # mirror back
    assert d == ("diag-" if "NORTH_TO_SOUTH" in name else "diag+")
    assert {(x0 + 1, x0 + 1), (x0 + 10, x0 + 10)} <= solid           # the towers on the end tiles
    assert not solid & {(x0 + 6, x0 + 6), (x0 + 5, x0 + 6), (x0 + 6, x0 + 5)}   # the opening in the middle
    assert not solid & {(x0, x0 + 11), (x0 + 11, x0)}                 # the corners off the diagonal stay free
    assert all(abs(x - z) <= T // 2 for x, z in solid)


def test_wall_tiles_decide_the_diagonal_of_a_gate():
    assert gate_solid("GATE_WEST_TO_EAST", [(10, 6), (6, 10)])[1] == "diag-"
    assert gate_solid("GATE_NORTH_TO_SOUTH", [(10, 10), (6, 6)])[1] == "diag+"
    assert gate_solid("GATE_SOUTHWEST_TO_NORTHEAST", [(10, 8), (5, 8)])[1] is False


def test_farm_has_crop_rows():
    """A farm (#65): rows of wheat with bare furrows between them, a path around it. The rows turn with the map."""
    for turn in (0, 1):
        cols = aoe2mc.Columns(8, np.zeros((8, 8), np.int16), np.zeros((8, 8), np.float32), {0: "GRASS_1"}, 4, 3,
                              np.random.default_rng(1))
        buildings.TURN = turn
        try:
            E, _ = aoe2mc.place_objects([dict(kind="B", name="FARM", player=1, x=4.5, y=4.5, rotation=0.0, hero=False,
                                              garrisoned=False)], {}, cols, np.random.default_rng(1))
        finally:
            buildings.TURN = 0
        x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
        names = np.array([aoe2mc.B.states[i].split(":")[1].split("[")[0] for i in ids])
        assert Counter(names) == {"farmland": 100, "dirt_path": 44, "wheat": 50, "air": 94}   # air: no grass
        wx, wz = x[names == "wheat"], z[names == "wheat"]
        assert len(set(wx if turn == 0 else wz)) == 5 and len(set(wz if turn == 0 else wx)) == 10
        ages = Counter(aoe2mc.B.states[i] for i in ids[names == "wheat"])
        assert ages.most_common(1)[0][0].endswith("age=7]") and len(ages) > 1


@pytest.mark.parametrize("arch", sorted(buildings.ARCH))
def test_university_has_a_library(arch):
    """The university (#73) has bookshelves and lecterns with books in every architecture set."""
    cols = flat_columns()
    E = aoe2mc.Edits(cols)
    o = dict(kind="B", name="UNIVERSITY", player=1, x=8.5, y=8.5, rotation=0.0, hero=False, garrisoned=False)
    buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": arch}}, set(), {})
    names = Counter(aoe2mc.B.states[i].split(":")[1].split("[")[0] for i in np.concatenate([p[3] for p in E.parts]))
    assert names["bookshelf"] >= 4 and names["lectern"] >= 1


@pytest.mark.parametrize("arch", sorted(buildings.ARCH))
def test_house_is_furnished(arch):
    """A house (#249) has a bed in the player color and a lantern inside, and the cells inside the door stay free."""
    for v in range(4):
        cols = flat_columns()
        E = aoe2mc.Edits(cols)
        o = dict(kind="B", name="HOUSE", player=1, x=8.0 + v % 2, y=8.0 + v // 2, rotation=0.0, hero=False,
                 garrisoned=False)
        buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": arch}}, set(), {})
        last = {}
        for x, y, z, ids, _ in E.parts:
            for p in zip(x.tolist(), y.tolist(), z.tolist(), ids.tolist()):
                last[p[:3]] = aoe2mc.B.states[p[3]].split(":")[1]
        names = Counter(s.split("[")[0] for s in last.values())
        assert names["blue_bed"] == 2 and names["lantern"] >= 1, (arch, v)
        for (x, y, z), s in last.items():
            if s.endswith("_door[facing=south,half=lower,hinge=left,open=false]"):
                inside = [last.get((x, y, z - k), "air") for k in (1, 2)]
                assert all(t in ("air", "barrier") or t.endswith("_carpet") for t in inside), (arch, v, inside)


@pytest.mark.parametrize("module", ["buildings.py", "aoe2mc.py", "units.py"])
def test_no_function_name_twice(module):
    """Parallel PRs can each add a function with the same name without a merge conflict; the second one then hides
    the first (#338: two `furnish` functions broke the house)."""
    import ast
    import os
    tree = ast.parse(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), module)).read())
    names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    assert sorted({n for n in names if names.count(n) > 1}) == []


@pytest.mark.parametrize("name", ["YURT_A", "HUT_A", "PAVILION_A", "ARMY_TENT_A", "GREEK_COMMANDER_TENT"])
def test_tents_and_huts_are_furnished(name):
    """The yurt, the hut, the pavilion and the tents (#335) have furniture and a light inside."""
    cols = flat_columns()
    E = aoe2mc.Edits(cols)
    o = dict(kind="B", name=name, player=1, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False)
    buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": "western"}}, set(), {})
    names = Counter(aoe2mc.B.states[i].split(":")[1].split("[")[0] for i in np.concatenate([p[3] for p in E.parts]))
    assert names["campfire"] + names["lantern"] >= 1
    assert names["blue_bed"] + names["cartography_table"] + names["spruce_slab"] >= 1
