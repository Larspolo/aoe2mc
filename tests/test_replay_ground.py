"""A building of the live replay stands on the natural ground, not on the trees of its footprint (#870)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402


def world(tree):
    d = data([])
    if tree:                                   # "ground" over a tree is the top of its barriers and its trunk
        d["objects"] = [{"kind": "other", "name": "TREE_OAK", "player": 0, "tile": [7.5, 7.5]},
                        {"kind": "other", "name": "PLANT_SHRUB", "player": 0, "tile": [8.5, 7.5]}]
        rows = [r.split() for r in d["ground"]]
        for z in range(28, 32):
            for x in range(28, 32):
                rows[z][x] = "78"
        d["ground"] = [" ".join(r) for r in rows]
    return d


def ys(cmds):
    return [int(re.match(r"(?:setblock|fill) -?\d+ (-?\d+)", c).group(1)) for c in cmds if not c.startswith("fill") or " air" not in c]


def test_a_building_on_a_tree_clears_it_and_stands_on_the_ground():
    plain = replay.Replay(Fake(), world(False))
    r = replay.Replay(Fake(), world(True))
    e = build("HOUSE", (8.0, 8.0))
    want, got = plain.commands(e), r.commands(e)
    assert min(ys(got)) == min(ys(want)) and max(ys(got)) == max(ys(want))      # the floor on the natural ground
    logs = [c for c in got if "air replace #minecraft:logs" in c]
    assert logs and all(int(c.split()[2]) <= 70 for c in logs)                   # the tree goes, from its foot up
    assert [c for c in got if c not in logs and "#minecraft:leaves" not in c and "minecraft:bamboo" not in c] == want
    assert (7, 7) not in r.grid().trees
