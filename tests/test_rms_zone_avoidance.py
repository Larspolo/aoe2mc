"""Two lands of different zones keep apart by the smaller other_zone_avoidance_distance of the two (#5754): the
Definitive Random Map Scripting Guide says "When different values are used for two lands, the smaller one applies"."""
import numpy as np

import rmap


def grow_two(avoid_a, avoid_b, seed=1, n=40):
    owner = np.full((n, n), -1)
    lands = [{"id": 0, "cells": [(5, 20)], "target": 700, "clump": 0, "zone": 0, "avoid": avoid_a},
             {"id": 1, "cells": [(34, 20)], "target": 700, "clump": 0, "zone": 1, "avoid": avoid_b}]
    rmap.grow(owner, lands, np.ones((n, n), bool), np.random.default_rng(seed))
    a = np.argwhere(owner == 0)
    b = np.argwhere(owner == 1)
    return int(np.abs(a[:, None, :] - b[None, :, :]).max(axis=2).min())     # Chebyshev distance of the closest tiles


def test_lands_keep_the_smaller_avoidance_distance_apart():
    gap = grow_two(10, 6)
    assert gap >= 7                 # the smaller value (6): no tile of the other zone within 6 tiles
    assert gap < 11                 # and not the larger one (10): the lands come close


def test_a_land_without_the_attribute_can_touch_another():
    assert grow_two(10, 0) == 1     # a land with no attribute (0) does not keep the other land away
