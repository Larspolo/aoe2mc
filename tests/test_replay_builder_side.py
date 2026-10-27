"""Live replay: a builder whose walls close it in a pocket (walls and water) steps out to the open side of the new
wall, as in AoE2, so that its next order has a path on land (#1275)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402

VIL = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "u1", "ref": 7, "tile": [9.5, 8.5]}


def wall(t, a, b):
    return dict(build("PALISADE_WALL", t=t), kind="wall", tile=list(a), end=list(b), objects=[7],
                names=["VILLAGER_MALE"])


def test_builder_leaves_the_pocket_of_its_walls():
    d = data([])
    d["ground"] = [" ".join(["70"] * 40 + ["-"] * 24)] * 64              # water east of block x 40 (tile 10)
    d["objects"].append(VIL)
    r = replay.Replay(Fake(), d)
    r.commands(wall(1000, (9, 7), (9, 7)))                               # north: tile (8, 7) stays a diagonal gap
    r.commands(wall(2000, (8, 8), (8, 9)))                               # west
    v = r.units[7]
    assert v.cell == (38, 34) and r.map.path(v.cell, {(8, 8)})          # still open to the south
    r.commands(wall(3000, (9, 9), (9, 9)))                               # south: the pocket of tile (9, 8) closes
    assert not (36 <= v.cell[0] < 40 and 32 <= v.cell[1] < 36)           # out of the pocket
    assert r.map.path(v.cell, {(8, 8)}) is not None


def test_an_order_lets_a_unit_out_of_a_closed_pocket():
    """The record has the walk after the walls (a shore fisher in the pocket gets an order on a tree, #1275): the unit
    steps over the nearest wall and walks on land, it does not swim."""
    d = data([])
    d["ground"] = [" ".join(["70"] * 40 + ["-"] * 24)] * 64
    d["objects"].append(VIL)
    r = replay.Replay(Fake(), d)
    for k, (a, b) in enumerate([((9, 7), (9, 7)), ((8, 8), (8, 9)), ((9, 9), (9, 9))]):
        r.commands(dict(wall(1000 * k + 1000, a, b), objects=[]))      # no builder: the unit stays in the pocket
    v = r.units[7]
    assert v.cell == (38, 34) and r.map.path(v.cell, {(8, 8)}) is None
    r.commands(dict(time=5000, player=1, kind="move", objects=[7], tile=[2.5, 2.5], names=["VILLAGER_MALE"]))
    assert not (36 <= v.cell[0] < 40 and 32 <= v.cell[1] < 36) and v.path and v.path[-1] == (10, 10)
