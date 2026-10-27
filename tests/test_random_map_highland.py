"""--random-map highland: a river between the players with shallow fords (#1174)."""
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


@pytest.mark.parametrize("seed", range(1, 11))
def test_the_river_separates_the_players_and_the_fords_join_them(seed):
    d = rmap.random_map("highland", seed, 2)
    t = np.array(d["terrain"])
    a, b = ((int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == "TOWN_CENTER")
    land = ~np.isin(t, [T["WATER"], T["SHALLOW"]])                        # forest too: the river crosses the whole map
    assert b not in reach(t, a, land)
    open_land = ~np.isin(t, [T["WATER"]] + list(rmap.FOREST_TREES))       # land without forest, and the fords
    assert b in reach(t, a, open_land)
    fords = (t == T["SHALLOW"]).sum()
    assert 3 * 7 <= fords <= 5 * 4 * 8 and (t == T["WATER"]).sum() > 400


@pytest.mark.parametrize("players", [2, 4, 8])
def test_no_start_object_is_on_water_or_forest(players):
    d = rmap.random_map("highland", 7, players)
    t = np.array(d["terrain"])
    bad = [T["WATER"], T["SHALLOW"]] + list(rmap.FOREST_TREES)
    start = [o for o in d["objects"] if not o["name"].startswith("TREE") and "FISH" not in o["name"]]
    assert {o["name"] for o in start} >= {"TOWN_CENTER", "VILLAGER_MALE", "GOLD_MINE"}
    assert not any(t[int(o["x"]), int(o["y"])] in bad for o in start)
