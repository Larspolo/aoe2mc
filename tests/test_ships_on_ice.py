"""A ship on frozen water stands on the ice and is not a unit in a block (#1024)."""
from collections import Counter

import numpy as np

import aoe2mc
import units


def ship(name, frozen, deck=False):
    """Place one ship on a 4 × 4 sea; return its y, the wtop of its column and the count of MOVED."""
    cols = aoe2mc.Columns(4, np.zeros((4, 4), np.int16), np.zeros((4, 4), np.float32),
                          {0: "ICE_NAVIGABLE" if frozen else "WATER_DEEP"}, 4, 3, np.random.default_rng(1))
    vol = aoe2mc.build_chunk(0, 0, cols, None)[1]
    o = dict(kind="U", name=name, player=1, x=1.5, y=1.5, rotation=0.0, hero=False, garrisoned=False)
    ents = [e for c in aoe2mc.plan_units([o], {}, cols, np.random.default_rng(1), Counter()).values() for e in c]
    x, z = int(ents[0][1]), int(ents[0][2])
    wtop = int(cols.wtop[x, z])
    if deck:                                    # a solid block above the ice, like a bridge deck
        vol[wtop + 1 - aoe2mc.MIN_Y, z, x] = aoe2mc.B("stone")
    passable = aoe2mc.passable_states(aoe2mc.B.states)
    before = sum(aoe2mc.MOVED.values())
    aoe2mc.entity_chunk(0, 0, ents, cols, vol, passable)
    return float(units.top_entity(ents[0][0])["Pos"][1]), wtop, sum(aoe2mc.MOVED.values()) - before


def test_ship_on_frozen_water_stands_on_the_ice_and_does_not_count():
    y, wtop, n = ship("TURTLE_SHIP", True)
    assert (y, n) == (wtop + 1, 0)


def test_ship_on_open_water_floats_as_before():
    y, wtop, n = ship("TURTLE_SHIP", False)
    assert (y, n) == (wtop + 0.5, 0)


def test_ship_on_frozen_water_under_a_deck_still_counts():
    y, wtop, n = ship("TURTLE_SHIP", True, deck=True)
    assert y > wtop + 2 and n == 1
