"""Groups of create_object in a random map script: number_of_groups, group_variance, the grouping (#3856)."""
import numpy as np
import pytest

import rmap

LAND = """<LAND_GENERATION>
base_terrain GRASS
<OBJECTS_GENERATION>
"""


def groups(objs, gap):
    """The objects joined by a distance of at most gap tiles."""
    left, out = list(objs), []
    while left:
        group = [left.pop()]
        for o in group:
            near = [p for p in left if max(abs(p["x"] - o["x"]), abs(p["y"] - o["y"])) <= gap]
            group += near
            left = [p for p in left if p not in near]
        out.append(group)
    return out


@pytest.mark.parametrize("seed", range(1, 4))
def test_two_tight_groups_of_six_bushes(seed):
    text = LAND + "create_object FORAGE { number_of_objects 6 number_of_groups 2 set_tight_grouping set_gaia_object_only }"
    bushes = [o for o in rmap.generate(text, seed, size=100, warn=lambda m: pytest.fail(m))["objects"]
              if o["name"] == "FORAGE_BUSH"]
    assert len(bushes) == 12 and {o["player"] for o in bushes} == {0}
    found = groups(bushes, 1)
    assert sorted(len(g) for g in found) == [6, 6]


@pytest.mark.parametrize("seed", range(1, 6))
def test_variance_and_radius_of_loose_groups(seed):
    text = LAND + "create_object DEER { number_of_objects 6 number_of_groups 1 group_variance 2 group_placement_radius 3 }"
    deer = [o for o in rmap.generate(text, seed, size=100, warn=lambda m: pytest.fail(m))["objects"] if o["name"] == "DEER"]
    assert 4 <= len(deer) <= 8
    mid = deer[0]
    assert all(np.hypot(o["x"] - mid["x"], o["y"] - mid["y"]) <= 3 for o in deer)


def test_without_groups_each_object_is_alone():
    text = LAND + "create_object DEER { number_of_objects 5 }"
    assert len([o for o in rmap.generate(text, 1, size=100)["objects"] if o["name"] == "DEER"]) == 5
