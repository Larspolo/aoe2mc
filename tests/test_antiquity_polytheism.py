"""Polytheism of Antiquity Mode (#3982): the Priests walk faster, as in Return of Rome; a Hoplite keeps its speed.
The rule modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import train
server, g = setup(food=1000, age=3)
names = ("PRIEST", "HOPLITE")
before = {n: train.speed(g, n) for n in names}
g.techs.add("POLYTHEISM")
print(json.dumps({"before": before, "after": {n: train.speed(g, n) for n in names}}))
'''


def test_polytheism_makes_the_priests_faster_only():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["after"]["PRIEST"] > out["before"]["PRIEST"]
    assert out["after"]["HOPLITE"] == out["before"]["HOPLITE"]
