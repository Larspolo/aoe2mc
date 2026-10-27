"""--random-map gold_rush and highland: the wolves of the AoE2 maps, as GREY_WOLF of Gaia (#2019)."""
import numpy as np
import pytest

import rmap

NOT_LAND = list(rmap.FOREST_TREES) + [rmap.TERRAINS["WATER"], rmap.TERRAINS["SHALLOW"]]


def wolves(d):
    tcs = [o for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    t = np.array(d["terrain"])
    out = [o for o in d["objects"] if o["name"] == "GREY_WOLF"]
    for o in out:
        assert o["player"] == 0
        assert t[int(o["x"]), int(o["y"])] not in NOT_LAND, o
        assert all(np.hypot(o["x"] - tc["x"], o["y"] - tc["y"]) >= 25 for tc in tcs), o
    return out


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_gold_rush_has_wolves_near_the_gold(seed, players):
    d = rmap.random_map("gold_rush", seed, players)
    mid, near = d["size"] / 2, rmap.GOLDS["gold_rush"][0] + 4
    middle = [o for o in wolves(d) if np.hypot(o["x"] - mid, o["y"] - mid) <= near]
    assert len(middle) >= 2 * players


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
def test_highland_has_a_wolf_per_player(seed, players):
    assert len(wolves(rmap.random_map("highland", seed, players))) >= players - 1


@pytest.mark.parametrize("kind", ["islands", "mediterranean", "nomad"])
def test_maps_without_predators_have_no_wolf(kind):
    assert not wolves(rmap.random_map(kind, 1, 2))
