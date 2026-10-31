"""Each object constant of random_map.def (the key "object" of data/rmap.jsonl, rmap.OBJECTS) places objects in
create_object, with no warning, on land or on water (a fish, a dock), #4929."""
import numpy as np

import rmap


def test_each_object_constant_places_an_object():
    water = rmap.TERRAINS["WATER"]
    for word in rmap.OBJECTS:
        for terrain in (0, water):
            warns = []
            out = rmap.objects([("create_object", [word], {})], rmap.OBJECTS, np.full((20, 20), terrain), [],
                               np.random.default_rng(1), warns.append)
            if out and warns == []:
                break
        else:
            raise AssertionError((word, warns))
