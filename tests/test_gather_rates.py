"""game/gather.py: each resource has its AoE2 work rate (#413)."""
import measure_gather
import pytest
from test_gather_farms import farm_map
from test_gather_mines import mine_map

from game import gather


def test_default_work_seconds_are_the_aoe2_rates_at_normal_speed():
    assert all(gather.WORK_SECONDS[r] == pytest.approx(1 / (w * gather.NORMAL)) for r, w in gather.AOE2_WORK.items())
    assert measure_gather.AOE2_WORK == gather.AOE2_WORK and measure_gather.WORK_SECONDS == gather.WORK_SECONDS
    _, g = mine_map()
    assert gather.Gather(g.game, {"tile_size": 1, "ground": [], "objects": []}).chop == gather.WORK_SECONDS
    assert set(gather.Gather(g.game, {"tile_size": 1, "ground": [], "objects": []}, chop=0.5).chop.values()) == {0.5}


def ticks_per_load(g, uuid, tile):
    """Ticks in the work state for one load of 10."""
    g.select(uuid)
    g.send(tile)
    n = 0
    for _ in range(5000):
        g.step()
        v = g.villagers[uuid]
        n += v.state == "chop"
        if v.state == "to_drop":
            return n


def test_each_resource_takes_its_own_time():
    _, g = mine_map()
    g.chop = {"wood": 1.0, "food": 1.0, "farm": 1.0, "gold": 0.5, "stone": 2.0}
    gold = ticks_per_load(g, "v", (12, 12))
    _, g = mine_map()
    g.chop = {"wood": 1.0, "food": 1.0, "farm": 1.0, "gold": 0.5, "stone": 2.0}
    stone = ticks_per_load(g, "v", (12, 18))
    assert gold == pytest.approx(10 * 0.5 / 0.25, abs=1) and stone == pytest.approx(10 * 2.0 / 0.25, abs=1)
    _, g = farm_map()
    g.chop = {"wood": 1.0, "food": 0.25, "farm": 0.75, "gold": 1.0, "stone": 1.0}
    assert ticks_per_load(g, "v", (10, 10)) == pytest.approx(10 * 0.75 / 0.25, abs=1)    # a farm, not a bush
