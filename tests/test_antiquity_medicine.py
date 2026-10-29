"""Medicine of Antiquity Mode (#3984): after it, a monk heals more than RATE hit points per AoE2 second; without it, RATE. The
rule modules read their data at import, so the Antiquity check runs in one child process."""
import json

from test_antiquity_setting import child
from test_monk_heal import run, setup

from game import monk

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_monk_heal import run, setup
server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
g.techs.add("MEDICINE")
run(g, 4)
print(json.dumps({"hp": server.entities["a"]["Health"]}))
'''


def test_medicine_increases_the_heal_rate_in_antiquity_mode():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["hp"] > 10 + 4 * monk.RATE                              # more than without Medicine


def test_medicine_is_no_change_outside_antiquity_mode():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    g.techs.add("MEDICINE")
    run(g, 4)
    assert server.entities["a"]["Health"] == 10 + 4 * monk.RATE
