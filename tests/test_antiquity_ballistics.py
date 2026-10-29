"""Ballistics in Antiquity Mode (#3922, epic #3887): after the research, the missiles of the player hit moving targets.
The rule modules read their data at import, so the check runs in a child process with AOE2MC_RULES=antiquity."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import train
server, g = setup(food=1000, age=0)
g.techs.update({"TOOL_AGE", "BRONZE_AGE", "IRON_AGE"})          # the Iron Age (the key "age" of Ballistics is 3)
g.paper = True
g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
g.sites.append({"name": "GOVERNMENT_CENTER", "player": 1, "footprint": [10, 13, 8, 11], "done": True})
assert train.queue(g, "Steve", (11, 9), "BALLISTICS")
train.tick(g, train.TRAIN_TIMES["BALLISTICS"] + 1)
print(json.dumps({"researched": "BALLISTICS" in g.techs, "log": [c for c in server.log if "ballistics" in c]}))
'''


def test_the_research_of_ballistics_turns_on_the_aim_of_the_plugin_in_antiquity_mode():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["researched"]
    assert out["log"] == ["aoe ballistics p1 on"]
