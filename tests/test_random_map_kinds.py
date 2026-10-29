"""--random-map arena and black_forest: own generators of the land (#1061)."""
from collections import Counter

import numpy as np
import pytest

import aoe2mc
import rmap

FOREST = rmap.TERRAINS["FOREST"]


def tiles(d, name):
    return {(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == name}


@pytest.mark.parametrize("players", [2, 4, 8])
def test_arena_closes_each_player_in_a_wall_circle_with_forest_inside(players):
    d = rmap.random_map("arena", 3, players)
    n, t = d["size"], np.array(d["terrain"])
    walls = Counter(o["player"] for o in d["objects"] if o["name"] == "STONE_WALL")
    assert set(walls) == set(range(1, players + 1)) and min(walls.values()) > 80
    wall = tiles(d, "STONE_WALL")
    for tc in (o for o in d["objects"] if o["name"] == "TOWN_CENTER"):
        # a walk of 4 steps from the town center never leaves the circle: it reaches only the inside and the map edge
        seen, todo = {(tc["x"], tc["y"])}, [(tc["x"], tc["y"])]
        while todo:
            x, y = todo.pop()
            for dx, dy in rmap.STEPS:
                c = (x + dx, y + dy)
                if 0 <= c[0] < n and 0 <= c[1] < n and c not in seen and c not in wall:
                    seen.add(c)
                    todo.append(c)
        assert all(np.hypot(x + 0.5 - tc["x"], y + 0.5 - tc["y"]) <= rmap.WALLS["arena"] for x, y in seen)
        assert sum(t[c] == FOREST for c in seen) > 150, tc                       # its wood is inside the wall
        assert not any(t[c] == FOREST for c in wall)
    inside = np.zeros((n, n), bool)
    x, y = np.mgrid[0:n, 0:n] + 0.5
    for tc in (o for o in d["objects"] if o["name"] == "TOWN_CENTER"):
        inside |= np.hypot(x - tc["x"], y - tc["y"]) <= rmap.WALLS["arena"]
    assert not (t[~inside] == FOREST).any()                                     # open land between the circles
    for o in d["objects"]:                                                      # the start objects are inside
        if o["name"] not in ("RELIC", "STONE_WALL", "TREE_OAK_FOREST"):        # a relic is Gaia (#2018)
            assert inside[int(o["x"]), int(o["y"])] and t[int(o["x"]), int(o["y"])] != FOREST, o


def test_black_forest_is_mostly_forest_with_open_player_lands_and_paths():
    d = rmap.random_map("black_forest", 3)
    n, t = d["size"], np.array(d["terrain"])
    assert (t == FOREST).mean() > 0.5
    open_ = t != FOREST
    tcs = [(o["x"], o["y"]) for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    assert len(tcs) == 2
    # the open land of each player reaches the middle and the other player
    seen, todo = {tcs[0]}, [tcs[0]]
    while todo:
        x, y = todo.pop()
        for dx, dy in rmap.STEPS:
            c = (x + dx, y + dy)
            if 0 <= c[0] < n and 0 <= c[1] < n and c not in seen and open_[c]:
                seen.add(c)
                todo.append(c)
    assert tcs[1] in seen and (n // 2, n // 2) in seen
    n_ = Counter(o["name"] for o in d["objects"])
    sheep = next(c for name, c, *_ in rmap.START if name == "SHEEP")
    assert n_["GOLD_MINE"] and n_["STONE_MINE"] and n_["SHEEP"] == 2 * sheep and n_["TREE_OAK_FOREST"] == (t == FOREST).sum()


@pytest.mark.parametrize("kind", ["arena", "black_forest"])
def test_the_same_seed_gives_the_same_map(kind):
    assert rmap.random_map(kind, 5) == rmap.random_map(kind, 5)
    assert rmap.random_map(kind, 5)["terrain"] != rmap.random_map(kind, 6)["terrain"]


def test_the_cli_takes_the_new_kinds():
    for kind in ("arena", "black_forest"):
        size, terrain, *_, objects, players = aoe2mc.read_map(aoe2mc.RANDOM_MAP + kind, 7)
        assert size == 120 and sum(o["name"] == "TOWN_CENTER" for o in objects) == 2
