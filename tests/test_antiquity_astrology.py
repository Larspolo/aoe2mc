"""Astrology of Antiquity Mode (#3985): after it, a monk converts 1.3 times as fast (and heals 1.3 times as fast, the
key `heal_rate`). The rule modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_monk_convert import setup
from game import monk
server, g = setup(("foe", "MILITIA", 2, 8.5))
monk.convert_order(g, {"monk"}, "foe")
monk.convert(g, 0.5)
before = g.converting["monk"][1]
g.converting["monk"][1] = 0.0
g.techs.add("ASTROLOGY")
monk.convert(g, 0.5)
print(json.dumps({"before": before, "after": g.converting["monk"][1]}))
'''


def test_astrology_speeds_up_the_conversion_in_antiquity_mode():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert abs(out["after"] - 1.3 * out["before"]) < 1e-9
