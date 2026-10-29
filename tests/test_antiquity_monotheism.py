"""Monotheism of Antiquity Mode (#3986): the priests convert enemy buildings and enemy priests, as Redemption and
Atonement do in AoE2. The rule modules read their data at import, so the check runs in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_monk_redemption import fort
import monk
server, g, house = fort(("priest", "PRIEST", 2, 12.5))
state = lambda: [monk.convertible(g, "priest"), monk.convertible(g, house)]
before = state()
g.techs.add("MONOTHEISM")
print(json.dumps({"before": before, "after": state()}))
'''


def test_monotheism_lets_the_priests_convert_buildings_and_priests():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out == {"before": [False, False], "after": [True, True]}
