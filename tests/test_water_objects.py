"""Bridges, gates and walls that cross water (#192)."""
import numpy as np

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
    for x in range(26, 46):                                              # water flows under the deck
        assert not any(bx == x and bz == zc and y <= water for (bx, y, bz) in blocks)


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
