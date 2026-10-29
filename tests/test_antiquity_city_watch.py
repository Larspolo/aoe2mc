"""City Watch of Antiquity Mode (#3915): each own building sees 3 tiles more after City Watch, as in Return of Rome. The
Town Watch of AoE2 gives 4 (tests/test_town_watch.py). The rule modules read their data at import: the check runs in a
child process with AOE2MC_RULES=antiquity."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_town_watch import tiles
from game import combat
r = combat.sight("TOWN_CENTER")
before, after = tiles(()), tiles({"CITY_WATCH"})
out = {"before": [(42, 42 - r - k) in before for k in (3, 4)], "after": [(42, 42 - r - k) in after for k in (3, 4)]}
print(json.dumps(out))
'''


def test_city_watch_adds_3_tiles_of_line_of_sight():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["before"] == [False, False]                  # no watch: the sight of the town center ends at r
    assert out["after"] == [True, False]                    # r + 3 is seen, r + 4 is not
