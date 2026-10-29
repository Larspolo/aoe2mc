"""--random-map nomad: no town center, the villagers apart, a sea at the map edges (#1176, #2336)."""
from itertools import combinations

import numpy as np
import pytest

import rmap

T = rmap.TERRAINS


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_no_town_center_and_the_start_villagers_apart_and_a_sea(seed, players):
    d = rmap.random_map("nomad", seed, players)
    t = np.array(d["terrain"])
    n = t.shape[0]
    assert not any(o["name"] == "TOWN_CENTER" for o in d["objects"])
    assert t[n // 2, n // 2] != T["WATER"] and (t == T["WATER"]).mean() >= 0.15        # land in the middle (#2336)
    for p in range(1, players + 1):
        vils = [(o["x"], o["y"]) for o in d["objects"] if o["name"].startswith("VILLAGER") and o["player"] == p]
        assert len(vils) == sum(c for name, c, *_ in rmap.START if name.startswith("VILLAGER"))
        assert all(np.hypot(a[0] - b[0], a[1] - b[1]) >= 6 for a, b in combinations(vils, 2))


@pytest.mark.parametrize("players", [2, 4, 8])
def test_no_start_object_is_on_water_or_forest(players):
    d = rmap.random_map("nomad", 7, players)
    t = np.array(d["terrain"])
    bad = [T["WATER"], T["SHALLOW"]] + list(rmap.FOREST_TREES)
    start = [o for o in d["objects"] if not o["name"].startswith("TREE") and "FISH" not in o["name"]]
    assert {o["name"] for o in start} >= {"VILLAGER_MALE", "VILLAGER_FEMALE", "GOLD_MINE"}
    assert not any(t[int(o["x"]), int(o["y"])] in bad for o in start)
