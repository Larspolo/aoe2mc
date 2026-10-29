"""Architecture of Antiquity Mode (#3917): buildings +20 % hit points, builders work 33 % faster. The AoE2
Architecture does not change the build speed. The rule modules read their data at import: Antiquity runs in a child."""
import json
import math

from test_antiquity_setting import child

from game import build

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import build, train
server, g = setup(food=1000, age=0)
out = {}
for k in ("before", "after"):
    out[k] = {"hp": train.stats(g, "BARRACKS").hp}
    site = {"name": "HOUSE", "player": g.player, "footprint": [0, 1, 0, 1], "progress": 0.0, "sent": 0, "commands": []}
    build.rise(g, site, 1)
    out[k]["progress"] = site["progress"]
    g.techs.add("ARCHITECTURE")
print(json.dumps(out))
'''


def test_antiquity_architecture_gives_buildings_hp_and_build_speed():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["after"]["hp"] == round(out["before"]["hp"] * 1.2)
    assert math.isclose(out["after"]["progress"], out["before"]["progress"] * 1.33)


def test_the_aoe2_architecture_does_not_change_the_build_speed():
    assert "ARCHITECTURE" not in build.BUILD_RATE
