"""Record Game (#3001): a new object takes an ID above every object of the world, a tree too."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import record  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 1, "tile": [4.0, 4.0], "footprint": [8, 8, 24, 24]}
VIL = {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "ref": 2, "uuid": "u-vil", "tile": [10.0, 10.0]}
TREE = {"kind": "other", "name": "TREE_OAK", "ref": 3, "tile": [40.0, 40.0]}


def test_a_new_villager_takes_an_ID_above_a_tree(tmp_path):
    d = data([])
    del d["timeline"]                                                  # a converted scenario has no timeline
    d["objects"] += [TC, VIL, TREE]
    g = types.SimpleNamespace(data=d, player=1, map=types.SimpleNamespace(T=4))
    path = str(tmp_path / "game.jsonl")
    record.start([g], path)
    record.queued(g, "VILLAGER_MALE", (8, 24, 8, 24))                  # the town center
    record.tick(g, 25)
    record.trained(g, "u-villager")
    record.ordered(g, "move", {"u-villager"}, cell=(40, 44))
    g.record.f.close()
    refs, _ = record.load(path)
    assert refs["u-villager"] > 3                                      # not the ID of the tree
    d = record.apply(d, path)
    move = next(e for e in d["timeline"] if e["kind"] == "move")
    assert move["names"] == ["VILLAGER_MALE"]
    r = replay.Replay(Fake(), d, ai=True)
    spawn, = r.spawns()                                                # the villager appears first, then it walks
    assert spawn["name"] == "VILLAGER_MALE"
    r.commands(spawn)
    cmds = r.commands(move)                                            # the move binds the ID to the new villager
    uuid = r.units[refs["u-villager"]].uuid
    assert any(c.startswith(f"aoe moveto {uuid} ") for c in cmds)     # the plugin walks it
