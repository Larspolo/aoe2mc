"""--random-map mediterranean: a sea in the middle of the map, the players on the coast around it (#1175)."""
import numpy as np
import pytest

import rmap

T = rmap.TERRAINS


def reach(t, start, ok):
    """The tiles that a walk of 4 steps from start reaches over the tiles where ok is True."""
    n = t.shape[0]
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for dx, dy in rmap.STEPS:
            c = (x + dx, y + dy)
            if 0 <= c[0] < n and 0 <= c[1] < n and c not in seen and ok[c]:
                seen.add(c)
                todo.append(c)
    return seen


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_the_sea_is_in_the_middle_and_the_land_joins_the_players(seed, players):
    d = rmap.random_map("mediterranean", seed, players)
    t = np.array(d["terrain"])
    n, water = t.shape[0], t == T["WATER"]
    assert water[n // 2, n // 2] and water.mean() >= 0.15
    tcs = [(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    x, y = np.nonzero(water)
    assert all(np.hypot(x - a, y - b).min() <= 25 for a, b in tcs)
    open_land = ~np.isin(t, [T["WATER"]] + list(rmap.FOREST_TREES))
    walk = reach(t, tcs[0], open_land)
    assert all(c in walk for c in tcs)
    beach = t == T["BEACH"]
    assert beach.sum() > 0 and not (beach & ~rmap.dilate(water, 1)).any()


@pytest.mark.parametrize("players", [2, 4, 8])
def test_no_start_object_is_on_water_or_forest(players):
    d = rmap.random_map("mediterranean", 7, players)
    t = np.array(d["terrain"])
    bad = [T["WATER"], T["SHALLOW"]] + list(rmap.FOREST_TREES)
    start = [o for o in d["objects"] if not o["name"].startswith("TREE") and "FISH" not in o["name"]]
    assert {o["name"] for o in start} >= {"TOWN_CENTER", "VILLAGER_MALE", "GOLD_MINE"}
    assert not any(t[int(o["x"]), int(o["y"])] in bad for o in start)
