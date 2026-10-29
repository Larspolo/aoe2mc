"""Aristocracy of Antiquity Mode (#3921): the Academy units walk 0.225 tiles per second faster, as in Return of Rome; a
Barracks unit keeps its speed. The rule modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import ai, train
server, g = setup(food=1000, age=3)
tiles = lambda n: ai.walk_speed(n, 1, 1) * train.speed(g, n)
before = {n: tiles(n) for n in ("HOPLITE", "CENTURION", "CLUBMAN")}
g.techs.add("ARISTOCRACY")
print(json.dumps({"base": {n: ai.walk_speed(n, 1, 1) for n in before}, "before": before,
                  "after": {n: tiles(n) for n in before}}))
'''


def test_aristocracy_adds_speed_to_the_academy_units_only():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["before"] == out["base"]
    for n in ("HOPLITE", "CENTURION"):
        assert abs(out["after"][n] - out["base"][n] - 0.225) < 1e-9, n
    assert out["after"]["CLUBMAN"] == out["base"]["CLUBMAN"]
