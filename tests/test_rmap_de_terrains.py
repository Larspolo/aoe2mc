"""The DE terrain constants of the owner's maps (#4930): each gives its terrain ID as base_terrain."""
import json

import numpy as np
import pytest

import rmap

NAMES = ["DLC_MANGROVESHALLOW", "ICY_SHORE", "DLC_CRACKED", "MEDITERRANEAN_FOREST", "DLC_NEWSHALLOW",
         "DLC_ROADGRAVEL"]
IDS = {r["name"]: r["terrain"] for r in map(json.loads, open("data/rmap.jsonl")) if "terrain" in r}


@pytest.mark.parametrize("name", NAMES)
def test_a_de_constant_as_base_terrain_gives_its_terrain_id(name):
    d = rmap.generate(f"<LAND_GENERATION>\nbase_terrain {name}\n", 1, players=2, size=60,
                      warn=lambda m: pytest.fail(m))
    assert np.all(np.asarray(d["terrain"]) == IDS[name])


def test_the_new_shallows_are_wet_and_the_new_forest_has_trees():
    assert {IDS["DLC_MANGROVESHALLOW"], IDS["DLC_NEWSHALLOW"]} <= set(rmap.wet_ids())
    assert IDS["MEDITERRANEAN_FOREST"] in rmap.FOREST_TREES
