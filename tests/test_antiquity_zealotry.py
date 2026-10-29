"""Zealotry of Antiquity Mode (#3887): its villagers carry 8 less (gather.CARRY). The rule modules read their data at
import, so the check runs in one child process (as tests/test_antiquity_aristocracy.py)."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_civ_work import setup
g = setup("FRANKS")
before = {"wood": g.limit("wood"), "gold": g.limit("gold"), "farm": g.limit("food", "farm")}
g.techs.add("ZEALOTRY")
after = {"wood": g.limit("wood"), "gold": g.limit("gold"), "farm": g.limit("food", "farm")}
print(json.dumps({"before": before, "after": after}))
'''


def test_zealotry_makes_the_villagers_carry_8_less():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["before"] == {"wood": 10, "gold": 10, "farm": 10}
    assert out["after"] == {"wood": 2, "gold": 2, "farm": 2}
