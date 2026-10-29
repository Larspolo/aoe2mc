"""City Watch of Antiquity Mode (#3915): each own building sees more tiles after City Watch, as in Return of Rome
(the Town Watch of AoE2: tests/test_town_watch.py). The rule modules read their data at import: the check runs in a
child process with AOE2MC_RULES=antiquity."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_town_watch import tiles
before, after = tiles(()), tiles({"CITY_WATCH"})
print(json.dumps({"more": before < after}))
'''


def test_city_watch_adds_line_of_sight():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["more"]                                      # the buildings see more tiles
