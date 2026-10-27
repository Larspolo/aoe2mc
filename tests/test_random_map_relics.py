"""rmap.random_map puts the relics of AoE2 on each kind (#2018): 3 + 1 per player, on free land, far from the starts."""
import numpy as np
import pytest

import rmap

LAND = list(rmap.FOREST_TREES) + [rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]]


@pytest.mark.parametrize("kind", sorted(rmap.GENERATORS))
@pytest.mark.parametrize("players", [2, 4])
def test_each_kind_has_its_relics_on_land_far_from_each_start(kind, players):
    missing = 0
    for seed in range(1, 11):
        d = rmap.random_map(kind, seed, players)
        terrain, objects = np.array(d["terrain"]), d["objects"]
        relics = [o for o in objects if o["name"] == "RELIC"]
        missing += 3 + players - len(relics)
        assert 3 + players - len(relics) <= 1, (kind, seed)
        starts = [o for o in objects if o["name"] == "TOWN_CENTER" or kind in rmap.NOMADS and
                  o["name"].startswith("VILLAGER")]
        assert starts
        for r in relics:
            assert r["player"] == 0 and terrain[int(r["x"]), int(r["y"])] not in LAND, (kind, seed, r)
            assert all(np.hypot(r["x"] - s["x"], r["y"] - s["y"]) >= 20 for s in starts), (kind, seed, r)
            assert all(np.hypot(r["x"] - o["x"], r["y"] - o["y"]) >= 15 for o in relics if o is not r)
    assert missing <= 1, kind


def test_the_same_seed_gives_the_same_relics():
    a, b = (rmap.random_map("arabia", 7, 3)["objects"] for _ in range(2))
    assert [o for o in a if o["name"] == "RELIC"] == [o for o in b if o["name"] == "RELIC"]


def test_the_relics_change_no_other_object():
    d = rmap.random_map("nomad", 3, 2)
    keep = rmap.relics
    try:
        rmap.relics = lambda *a: []
        assert rmap.random_map("nomad", 3, 2)["objects"] == [o for o in d["objects"] if o["name"] != "RELIC"]
    finally:
        rmap.relics = keep
