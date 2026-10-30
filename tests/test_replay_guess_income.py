"""The live estimate counts the income of the villagers with a resource but no gather step (#4627): most villagers of
a record do not work in the replay. The record plays in real time to 23:00 with a fake clock."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")


def test_the_wood_estimate_stays_above_0():
    end = 23 * 60000
    timeline = [e for e in aoe2mc.read_timeline(REC) if e["time"] <= end]
    d = data(timeline + [dict(time=end + 1000, player=1, kind="chat", text="end")], n=480)
    kinds = {"O": "other"}                 # the names of aoe2mc.json: the trees
    d["objects"] = [dict(o, kind=kinds.get(o["kind"], o["kind"]), tile=[o["x"], o["y"]]) for o in aoe2mc.read_record(REC)[5]]
    d["players"]["2"]["arch"] = "western"       # data() has "meso", which buildings.ARCH lacks
    game = Clock()
    r = replay.Replay(game, d, ai=True)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, bar=True)
    assert all(r.resources(p)["wood"] >= 0 for p in (1, 2)), {p: r.resources(p) for p in (1, 2)}
