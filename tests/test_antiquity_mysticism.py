"""Mysticism of Antiquity Mode (#3983): the priests get more hit points, the other units keep theirs. The rule
modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import combat, train
server, g = setup(food=1000, age=0)
g.techs.add("MYSTICISM")
print(json.dumps({"priest": train.stats(g, "PRIEST").hp, "base": combat.stats("PRIEST").hp,
                  "hoplite": train.stats(g, "HOPLITE").hp, "hoplite_base": combat.stats("HOPLITE").hp}))
'''


def test_mysticism_gives_hit_points_to_the_priests_only():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["priest"] > out["base"]
    assert out["hoplite"] == out["hoplite_base"]
