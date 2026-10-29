"""Live replay: a villager that an ORDER sends to a farm, or that builds a farm, farms it at the AoE2 rate (#719).
Fake RCON."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

VIL = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [2.5, 10.5]}
FARM = {"kind": "building", "name": "FARM", "player": 1, "ref": 40, "tile": [6.5, 10.5], "footprint": [20, 36, 32, 48]}
STEP = 1000 / gather.AOE2_WORK["farm"]                                  # game ms per food


def play(timeline, end, objects=(FARM,), ai=False):
    """Play the timeline until game time `end` (ms): the last event is a chat line then."""
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, *objects]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game.sent


def order(t, target, tile=(6.5, 10.5)):
    return dict(time=t, player=1, kind="order", objects=[7], target=target, tile=list(tile), names=["VILLAGER_MALE"])


def farm_build(t=0):
    return dict(time=t, player=1, kind="build", type=50, name="FARM", tile=[10.5, 4.5], objects=[7],
                names=["VILLAGER_MALE"])


def hits(sent):
    return [c for c in sent if c.startswith("particle") and "wheat" in c]


@pytest.mark.parametrize("ai", [False, True])
def test_an_order_on_a_start_farm_farms_at_the_aoe2_rate(ai):
    r, sent = play([order(0, 40)], 120000, ai=ai)
    tile = (6, 10)
    food = gather.FARM_FOOD - r.map.farms[tile]
    due = r.working[7]
    assert 0 < due - (food + 1) * STEP < 10000                        # it walked about 10 blocks first
    assert due - STEP <= 120000 < due
    assert len(hits(sent)) == food > 0
    assert r.units[7].cell in r.crew.goals(tile)                       # it stands on the farm
    assert any("wheat[age=6] replace minecraft:wheat" in c for c in sent)     # gather.Gather.harvest
    assert r.crew.crops[tile] == math.ceil(7 * r.map.farms[tile] / gather.FARM_FOOD) < 7


def test_the_farmer_walks_over_the_farm():
    r, sent = play([order(0, 40)], 60000)
    tps = [c for c in sent if c.startswith("tp u1")]
    cells = {tuple(int(float(c.split()[k])) for k in (2, 4)) for c in tps}
    assert len(cells & r.crew.goals((6, 10))) > 5                       # gather.Gather.tend: one cell per food


def test_the_builders_of_a_farm_farm_it():
    r, sent = play([farm_build()], 60000, objects=())
    assert len(r.map.farms) == 1
    tile, = r.map.farms
    food = gather.FARM_FOOD - r.map.farms[tile]
    assert food > 0 and len(hits(sent)) == food and 7 in r.working
    assert r.units[7].cell in r.crew.goals(tile)


def test_an_order_on_a_farm_of_the_replay():
    tl = [farm_build(), dict(time=1000, player=1, kind="move", objects=[7], tile=[1.5, 1.5], names=["VILLAGER_MALE"]),
          order(20000, 99, tile=(10.5, 4.5))]                           # 99: a new ID, not in the start state
    r, sent = play(tl, 80000, objects=())
    tile, = r.map.farms
    food = gather.FARM_FOOD - r.map.farms[tile]
    assert 0 < food <= 60000 / STEP and 7 in r.working


def test_an_empty_farm_becomes_dirt_and_the_farmer_stops():
    r, sent = play([order(0, 40)], 700000)
    assert r.map.farms[(6, 10)] == 0 and 7 not in r.working
    assert len(hits(sent)) == gather.FARM_FOOD
    assert any("air replace minecraft:wheat" in c for c in sent)
    assert any("minecraft:dirt replace minecraft:farmland" in c for c in sent)


def test_a_deleted_farm_stops_its_farmer():
    tl = [order(0, 40), dict(time=30000, player=1, kind="delete", objects=[40], names=["FARM"])]
    r, sent = play(tl, 90000)
    assert (6, 10) not in r.map.farms and 7 not in r.working
    assert len(hits(sent)) <= 30000 / STEP
