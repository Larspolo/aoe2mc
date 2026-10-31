"""The fish names of data/rmap.jsonl are constants of a random map script (#5070)."""
import numpy as np

import rmap

FISH = sorted({r["name"] for r in rmap.RMAP if "fish" in r or r.get("shore_fish")})
LAND = "<LAND_GENERATION>\nbase_terrain WATER\n"


def test_create_object_of_each_fish_places_it():
    for name in FISH:
        d = rmap.generate(LAND + f"<OBJECTS_GENERATION>\ncreate_object {name} {{ number_of_objects 1 }}\n", 1)
        assert [o["name"] for o in d["objects"]] == [name]


def test_const_of_shore_fish():
    rmap.generate(f"#const X {rmap.SHORE_FISH}\n" + LAND, 1)


def test_fish_stays_the_same():
    t = np.full((30, 30), rmap.TERRAINS["WATER"], np.int16)
    t[:5] = rmap.TERRAINS["BEACH"]
    a = rmap.fish(t, next(iter(rmap.FISH.values())), 2, np.random.default_rng(3))
    b = rmap.fish(t, next(iter(rmap.FISH.values())), 2, np.random.default_rng(3))
    assert a == b and {o["name"] for o in a} <= set(FISH)
