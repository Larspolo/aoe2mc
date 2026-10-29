"""--random-map gold_rush: open land, many gold mines in the middle and a forest ring around them (#1173)."""
from collections import Counter

import numpy as np
import pytest

import aoe2mc
import rmap

FOREST = rmap.TERRAINS["FOREST"]


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_gold_rush_has_gold_in_the_middle_and_forest_around_it(seed, players):
    d = rmap.random_map("gold_rush", seed, players)
    n, t = d["size"], np.array(d["terrain"])
    mid = n / 2
    gold = [o for o in d["objects"] if o["name"] == "GOLD_MINE" and np.hypot(o["x"] - mid, o["y"] - mid) <= 12]
    assert len(gold) >= 20
    tcs = [o for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    assert len(tcs) == players
    for tc in tcs:                                                    # forest on the line from the middle to the TC
        line = {(int(mid + s * (tc["x"] - mid)), int(mid + s * (tc["y"] - mid))) for s in np.linspace(0, 1, 2 * n)}
        assert any(t[c] == FOREST for c in line), (seed, players, tc)
    for o in d["objects"]:                                            # no object on water or forest, but the trees
        if not o["name"].startswith("TREE"):
            assert t[int(o["x"]), int(o["y"])] not in (FOREST, rmap.TERRAINS["WATER"]), o
    male = next(c for name, c, *_ in rmap.START if name == "VILLAGER_MALE")
    assert Counter(o["name"] for o in d["objects"])["VILLAGER_MALE"] == male * players


def test_gold_rush_lets_units_reach_the_gold():
    d = rmap.random_map("gold_rush", 3)
    n, t = d["size"], np.array(d["terrain"])
    tc = next(o for o in d["objects"] if o["name"] == "TOWN_CENTER")
    seen, todo = {(tc["x"], tc["y"])}, [(tc["x"], tc["y"])]
    while todo:                                                       # a walk on land without forest
        x, y = todo.pop()
        for dx, dy in rmap.STEPS:
            c = (x + dx, y + dy)
            if 0 <= c[0] < n and 0 <= c[1] < n and c not in seen and t[c] != FOREST:
                seen.add(c)
                todo.append(c)
    assert (n // 2, n // 2) in seen


def test_the_same_seed_gives_the_same_gold_rush_map():
    assert rmap.random_map("gold_rush", 5) == rmap.random_map("gold_rush", 5)
    assert rmap.random_map("gold_rush", 5)["terrain"] != rmap.random_map("gold_rush", 6)["terrain"]


def test_the_cli_takes_gold_rush():
    size, terrain, *_, objects, players = aoe2mc.read_map(aoe2mc.RANDOM_MAP + "gold_rush", 7)
    assert size == 120 and sum(o["name"] == "TOWN_CENTER" for o in objects) == 2
