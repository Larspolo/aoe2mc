"""Live replay: a villager that an ORDER sends to a tree, a fruit bush or a mine gathers there at the AoE2 rate (#631).
Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

VIL = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [2.5, 10.5]}
TREE = {"kind": "other", "name": "TREE_OAK", "player": 0, "ref": 20, "tile": [5.5, 10.5]}
BUSH = {"kind": "other", "name": "FRUIT_BUSH", "player": 0, "ref": 21, "tile": [5.5, 10.5]}
MINE = {"kind": "other", "name": "STONE_MINE", "player": 0, "ref": 22, "tile": [6.0, 10.0]}


def order(t, target):
    return dict(time=t, player=1, kind="order", objects=[7], target=target, names=["VILLAGER_MALE"])


def play(timeline, target, end, ai=False):
    """Play the timeline until game time `end` (ms): the last event is a chat line then. target: one object or a list."""
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [VIL] + (target if isinstance(target, list) else [target])
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: now[0], sleep=sleep, log=None)
    return r, game.sent


def hits(sent, block):
    return [c for c in sent if c.startswith("particle") and block in c]


@pytest.mark.parametrize("ai", [False, True])
def test_an_order_on_a_tree_chops_at_the_aoe2_wood_rate(ai):
    r, sent = play([order(0, 20)], TREE, 60000, ai)
    wood = gather.TREE_WOOD - r.map.trees[(5, 10)]
    step = 1000 / gather.AOE2_WORK["wood"]                             # game ms per wood
    due = r.working[7]
    arrive = due - (wood + 1) * step
    assert 0 < arrive < 10000                                          # it walked about 10 blocks first
    assert due - step <= 60000 < due
    assert len(hits(sent, "oak_log")) == wood > 0
    assert any(c.startswith("rotate u1 facing") for c in sent)
    assert any(c.startswith("setblock") and "spruce_log" in c for c in sent)   # the tree lies on the ground


def test_the_tree_falls_when_its_wood_is_used():
    r, sent = play([order(0, 20)], TREE, 300000)
    assert r.map.trees[(5, 10)] == 0 and 7 not in r.working
    assert len(hits(sent, "oak_log")) == gather.TREE_WOOD
    assert any("air replace minecraft:barrier" in c for c in sent)     # gather.Gather.fell


def test_a_mine_shrinks_and_goes():
    r, sent = play([order(0, 22)], MINE, 60000)
    stone = gather.MINES["STONE_MINE"][1] - r.map.mines["stone"][(6, 10)]
    assert 0 < stone <= 60 * gather.AOE2_WORK["stone"] + 1 and len(hits(sent, "minecraft:stone")) == stone
    r, sent = play([order(0, 22)], MINE, 1000000)
    assert r.map.mines["stone"][(6, 10)] == 0 and 7 not in r.working
    assert any("air replace minecraft:cobblestone" in c for c in sent)   # gather.Gather.dig


def test_a_bush_loses_its_berries():
    r, sent = play([order(0, 21)], BUSH, 450000)
    assert r.map.bushes[(5, 10)] == 0
    assert any("dead_bush replace minecraft:sweet_berry_bush" in c for c in sent)


def test_a_new_move_stops_the_work():
    tl = [order(0, 20), dict(time=30000, player=1, kind="move", objects=[7], tile=[1.5, 1.5], names=["VILLAGER_MALE"])]
    r, sent = play(tl, TREE, 90000)
    wood = gather.TREE_WOOD - r.map.trees[(5, 10)]
    assert 0 < wood <= 30000 * gather.AOE2_WORK["wood"] / 1000 and 7 not in r.working and not r.moving
    assert r.units[7].cell == (6, 6)


def test_an_order_on_a_unit_or_a_building_gathers_nothing():
    other = {"kind": "unit", "name": "VILLAGER_MALE", "player": 2, "uuid": "u2", "ref": 30, "tile": [6.5, 10.5]}
    r, sent = play([order(0, 30)], other, 60000)
    assert not r.working and not hits(sent, "")
