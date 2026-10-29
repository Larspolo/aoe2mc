"""The fish of the random maps with water (#1943). AoE2 wiki: "Highland": "fish live in the rivers (the species present
are Salmon)"; "Nomad (map)" and "Islands", infobox: "Fish = Shore Fish, Deep Fish" ("Shallow Fish" on Islands);
"Mediterranean": "a sea in its middle, that supports decent numbers of Fish (including Shore Fish)"."""
import numpy as np
import pytest

import rmap

T = rmap.TERRAINS


@pytest.mark.parametrize("players", [2, 4])
@pytest.mark.parametrize("seed", range(1, 11))
@pytest.mark.parametrize("kind", sorted(rmap.FISH))
def test_the_fish_are_on_water_with_shore_fish_at_the_beach_and_deep_fish_far_from_land(kind, seed, players):
    d = rmap.random_map(kind, seed, players)
    t = np.array(d["terrain"])
    water = t == T["WATER"]
    shore, deep, count = rmap.FISH[kind]
    fish = [o for o in d["objects"] if o["name"] in ("SHORE_FISH", deep)]
    cells = [(int(o["x"]), int(o["y"])) for o in fish]
    assert sum(o["name"] == deep for o in fish) == count * players
    assert sum(o["name"] == "SHORE_FISH" for o in fish) == shore * players
    assert all(water[c] for c in cells)
    beach, near_land = rmap.dilate(t == T["BEACH"], 1), rmap.dilate(~water, 2)
    assert all(beach[c] for c, o in zip(cells, fish) if o["name"] == "SHORE_FISH")
    assert not any(near_land[c] for c, o in zip(cells, fish) if o["name"] == deep)
    xy = np.array([(o["x"], o["y"]) for o in fish])
    gaps = np.hypot(*(xy[:, None] - xy[None]).transpose(2, 0, 1)) + np.eye(len(xy)) * 99
    assert gaps.min() >= 3


@pytest.mark.parametrize("kind", ["arabia", "arena", "black_forest", "gold_rush"])
def test_the_land_maps_have_no_fish(kind):
    assert not any("FISH" in o["name"] for o in rmap.random_map(kind, 1, 2)["objects"])

