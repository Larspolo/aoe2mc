"""Afterlife of Antiquity Mode (#3988): the priests get +3 tiles of conversion range and line of sight, as in AoE2 DE.
The rule modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
import combat   # test values: the line of sight of a monk is its range + 2 tiles (combat.sight, #5398)
combat.STATS["MONK"] = combat.STATS["MONK"]._replace(range=9)
from test_fog_seen import T, bare, circle
from test_monk_convert import setup
from game import monk, train
server, g = setup(("far", "MILITIA", 2, 5.5 + 11))                     # 11 tiles from the monk (tile size 1)
pos = g.positions(["monk", "far"])
near = {"before": monk.near(g, "monk", "far", pos)}
g.techs.add("AFTERLIFE")
near["after"] = monk.near(g, "monk", "far", pos)
server.entities["far"]["Pos"] = (5.5 + 12.5, 64.0, 5.5)
near["farther"] = monk.near(g, "monk", "far", g.positions(["monk", "far"]))
def tiles(techs):
    g = bare()
    g.soldiers, g.techs = {"m": "MONK", "a": "ARCHER"}, set(techs)
    return g.seen_tiles({"m": (20.5 * T, 70.0, 20.5 * T), "a": (80.5 * T, 70.0, 20.5 * T)})
before, after = tiles(()), tiles({"AFTERLIFE"})
print(json.dumps({"near": near, "value": train.value("reach", "AFTERLIFE", 0),
                  "sight": [circle(20, 20, 11) <= before, circle(20, 20, 14) <= after,
                            (20 + 15, 20) not in after, (20 - 14, 20) in after]}))
'''


def test_afterlife_adds_3_tiles_of_conversion_range_and_sight():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["value"] > 0
    assert out["near"] == {"before": False, "after": True, "farther": False}
    assert out["sight"] == [True, True, True, True]
