"""--random-map islands: one island for each player, water between the islands (#1209)."""
import numpy as np
import pytest

import rmap

T = rmap.TERRAINS


def reach(ok, start):
    """The tiles that a walk of 4 steps from start reaches over the tiles where ok is True."""
    n = ok.shape[0]
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
def test_each_player_has_an_own_island_with_a_coast(seed, players):
    d = rmap.random_map("islands", seed, players)
    t = np.array(d["terrain"])
    water = t == T["WATER"]
    tcs = [(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    assert len(tcs) == players and water.mean() >= 0.3
    for tc in tcs:
        island = reach(~water, tc)
        assert len(island) >= 400
        assert [c for c in tcs if c in island] == [tc]                    # no walk over land to another player
        assert any(water[c[0] + dx, c[1] + dy] for c in island for dx, dy in rmap.STEPS
                   if 0 <= c[0] + dx < t.shape[0] and 0 <= c[1] + dy < t.shape[0])   # a coast for a dock
    beach = t == T["BEACH"]
    assert beach.sum() > 0 and not (beach & ~rmap.dilate(water, 1)).any()


@pytest.mark.parametrize("players", [2, 4, 8])
def test_no_start_object_is_on_water_or_forest(players):
    d = rmap.random_map("islands", 7, players)
    t = np.array(d["terrain"])
    bad = [T["WATER"], T["SHALLOW"]] + list(rmap.FOREST_TREES)
    start = [o for o in d["objects"] if not o["name"].startswith("TREE")]
    assert {o["name"] for o in start} >= {"TOWN_CENTER", "VILLAGER_MALE", "GOLD_MINE"}
    assert not any(t[int(o["x"]), int(o["y"])] in bad for o in start)
    assert sum(o["name"] == "TOWN_CENTER" for o in start) == players
