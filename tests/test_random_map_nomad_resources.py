"""--random-map nomad: the resources of AoE2 Nomad scattered over the map (#1944): pairs of sheep, single boars, 3-deer
herds, 6-tile gold and stone mines, mostly away from the villagers, never on water or forest."""
import numpy as np
import pytest

import rmap

T = rmap.TERRAINS


def groups(objects, name):
    """The sizes of the groups of next tiles (8 neighbours) of the objects with this name."""
    left, sizes = {(int(o["x"]), int(o["y"])) for o in objects if o["name"] == name}, []
    while left:
        todo, k = [left.pop()], 0
        while todo:
            x, y = todo.pop()
            k += 1
            near = {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & left
            left -= near
            todo += near
        sizes.append(k)
    return sorted(sizes)


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_the_nomad_resources_are_scattered_in_their_groups(seed, players):
    d = rmap.random_map("nomad", seed, players)
    t, objs = np.array(d["terrain"]), d["objects"]
    for name, size, k in rmap.SCATTER:
        assert groups(objs, name) == [size] * (groups(objs, name) and len(groups(objs, name)))   # all of one size
        assert len(groups(objs, name)) >= k * players - 1, name        # at most one group with no space
    assert not any(o["player"] for o in objs if o["name"] in {s[0] for s in rmap.SCATTER})    # Gaia
    vils = np.array([(o["x"], o["y"]) for o in objs if o["name"].startswith("VILLAGER")])
    mines = np.array([(o["x"], o["y"]) for o in objs if o["name"] in ("GOLD_MINE", "STONE_MINE")])
    near = (np.hypot(*(mines[:, None] - vils[None]).transpose(2, 0, 1)) <= 15).any(1)
    assert near.mean() < 0.5
    bad = [T["WATER"], T["SHALLOW"]] + list(rmap.FOREST_TREES)
    land = {s[0] for s in rmap.SCATTER} | {"VILLAGER_MALE", "VILLAGER_FEMALE"}     # not the fish (#1943)
    assert not any(t[int(o["x"]), int(o["y"])] in bad for o in objs if o["name"] in land)


def test_the_other_kinds_keep_the_start_resources():
    d = rmap.random_map("arabia", 3, 2)
    sheep = next(c for name, c, *_ in rmap.START if name == "SHEEP")
    assert len([o for o in d["objects"] if o["name"] == "SHEEP" and o["player"] == 1]) == sheep
