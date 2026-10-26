"""--random-map arabia: a wood line and single trees near each town center, as in AoE2 (#1144)."""
import numpy as np
import pytest

import rmap

FOREST = rmap.TERRAINS["FOREST"]


@pytest.mark.parametrize("seed", range(1, 11))
def test_each_arabia_player_has_a_wood_line_and_single_trees(seed):
    d = rmap.random_map("arabia", seed)
    t, n = np.array(d["terrain"]), d["size"]
    x, y = np.mgrid[0:n, 0:n] + 0.5
    for tc in (o for o in d["objects"] if o["name"] == "TOWN_CENTER"):
        r = np.hypot(x - tc["x"], y - tc["y"])
        assert ((t == FOREST) & (r >= 7) & (r <= 13)).sum() >= 20
        single = [o for o in d["objects"] if o["name"].startswith("TREE") and t[int(o["x"]), int(o["y"])] != FOREST
                  and 4 <= np.hypot(o["x"] - tc["x"], o["y"] - tc["y"]) <= 7]
        assert 2 <= len(single) <= 4
        assert not ((t == FOREST) & (r < 7)).any()


@pytest.mark.parametrize("seed", range(1, 11))
def test_no_tree_is_on_a_start_object_or_a_town_center(seed):
    d = rmap.random_map("arabia", seed)
    t = np.array(d["terrain"])
    trees = {(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"].startswith("TREE")}
    for o in d["objects"]:
        if o["name"] == "TOWN_CENTER":                   # the 4 × 4 town center around its corner point
            cells = {(o["x"] + i, o["y"] + j) for i in range(-2, 2) for j in range(-2, 2)}
            assert not cells & trees and not any(t[c] == FOREST for c in cells)
        elif not o["name"].startswith("TREE"):
            assert (int(o["x"]), int(o["y"])) not in trees and t[int(o["x"]), int(o["y"])] != FOREST, o
