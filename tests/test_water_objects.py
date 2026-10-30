"""Bridges, gates and walls that cross water (#192), ships in a dock (#190)."""
import contextlib
import io

import numpy as np
import scenarios
import world_reader
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.units import UnitInfo

import aoe2mc

T, H = 4, 3


def river_columns(water_tiles, n=20):
    """Land at elevation 2 with a river of deep water at elevation 0 along tile y (the river lies in a trench)."""
    t = np.zeros((n, n), np.int16)
    t[list(water_tiles)] = 1
    elev = np.where(t == 1, 0, 2).astype(np.float32)
    return aoe2mc.Columns(n, t, elev, {0: "GRASS_1", 1: "WATER_DEEP"}, T, H, np.random.default_rng(1))


def place(cols, objects):
    base = dict(kind="B", player=1, rotation=0.0, hero=False, garrisoned=False)
    E, _ = aoe2mc.place_objects([dict(base, **o) for o in objects], {}, cols, np.random.default_rng(1))
    x, y, z, ids, _ = (np.concatenate(p) for p in zip(*E.parts))
    return {(int(a), int(b), int(c)): aoe2mc.B.states[i] for a, b, c, i in zip(x, y, z, ids)}


def test_bridge_deck_at_bank_height_with_water_below():
    cols = river_columns(range(6, 12))
    pieces = [("BRIDGE_A_BOTTOM", 5), ("BRIDGE_A_MIDDLE", 7), ("BRIDGE_A_MIDDLE", 9), ("BRIDGE_A_MIDDLE", 11),
              ("BRIDGE_A_TOP", 13)]
    blocks = place(cols, [dict(name=n, player=0, x=float(x), y=10.5) for n, x in pieces])
    zc = 42                                                              # the middle line of the deck
    water = int(cols.wtop[32, zc])
    bank = int(cols.top[4 * 4 - 1, zc])
    assert bank > water + 2                                              # the test river lies in a trench
    deck = {x: max(y for (bx, y, bz) in blocks if bx == x and bz == zc) for x in range(16, 56)}
    assert len(set(deck.values())) == 1                                  # one flat deck ...
    assert bank - 1 <= deck[16] <= bank                                  # ... at the height of the banks
    wet = {x for (x, y, z) in blocks if z == zc and y <= water and 26 <= x < 46}
    assert wet == set(range(28, 46, 4))                     # only the piers stand in the water, every tile (#455)
    for x in range(26, 46):                                 # water flows under the arches between the piers
        if x % 4:
            assert not any(bx == x and bz == zc and y <= water + 1 for (bx, y, bz) in blocks)


def test_gate_on_water_keeps_its_opening_and_walls_get_a_footing():
    cols = river_columns(range(5, 7))
    walls = [dict(name="STONE_WALL", x=x + 0.5, y=10.5) for x in (2, 3, 8, 9)]
    blocks = place(cols, walls + [dict(name="GATE_NORTHWEST_TO_SOUTHEAST", x=6.0, y=10.5),
                                  dict(name="STONE_WALL", x=5.5, y=14.5)])
    water = int(cols.wtop[22, 42])
    for x in range(20, 28):                                              # the opening of the gate: open water
        for y in range(water, water + 4):
            assert (x, y, 42) not in blocks, (x, y)
    top = int(cols.top[22, 58])                                          # a wall on water stands on the bed
    assert (22, top + 1, 58) in blocks and (22, int(cols.wtop[22, 58]), 58) in blocks


def dock_map(path):
    """Deep water with a shore in the north, a dock and a galley that stands in the dock (#190)."""
    scn = scenarios.new_scenario(16)
    for t in scn.map_manager.terrain:
        t.terrain_id = TerrainId.GRASS_1 if t.y < 4 else TerrainId.WATER_DEEP
    um = scn.unit_manager
    um.add_unit(PlayerId.ONE, BuildingInfo.DOCK.ID, x=8.5, y=8.5)
    um.add_unit(PlayerId.ONE, UnitInfo.GALLEY.ID, x=8.2, y=8.8)
    return scenarios.save(scn, path)


def test_ship_in_a_dock_moves_to_free_water(tmp_path):
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        aoe2mc.convert(dock_map(str(tmp_path / "d.aoe2scenario")), str(tmp_path / "W"))
    log = log.getvalue()
    assert "  units in a block (moved up): 0" in log
    assert "  units moved out of a building or obstacle: 1" in log
    w = world_reader.World(str(tmp_path / "W"))
    boats = [e for e in w.entities(flat=False) if "boat" in str(e["id"])]
    assert len(boats) == 1 and boats[0].get("Passengers")         # the crew rides the boat
    x, y, z = (float(v) for v in boats[0]["Pos"])
    for yy in (int(y), int(y) + 1, int(y) + 2):                   # the boat and its crew are in water or air
        name = w.block(int(x), yy, int(z)).split("[")[0]
        assert name in ("minecraft:water", "minecraft:air"), (x, yy, z, name)
