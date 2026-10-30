"""The Return of Rome technologies of Antiquity Mode (#3714, docs/research/antiquity.md, 1.5): the effects of
Toolworking, Leather Armor Infantry and Domestication.
The rule modules read their data at import, so the checks run in one child process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import gather, train
out = {}
server, g = setup(food=1000, age=0)
g.techs.update({"TOOL_AGE"})
g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
g.sites.append({"name": "STORAGE_PIT", "player": 1, "footprint": [10, 13, 8, 11], "done": True})
g.sites.append({"name": "MARKET", "player": 1, "footprint": [16, 19, 8, 11], "done": True})
before = {n: train.stats(g, n)._asdict() for n in ("CLUBMAN", "BOWMAN")}
for cell, name in [((11, 9), "TOOLWORKING"), ((11, 9), "LEATHER_ARMOR_INFANTRY"), ((17, 9), "DOMESTICATION")]:
    assert train.queue(g, "Steve", cell, name), name
    train.tick(g, train.TRAIN_TIMES[name] + 1)
    assert name in g.techs, name
out["before"], out["after"] = before, {n: train.stats(g, n)._asdict() for n in before}
g.map.building("FARM", (12, 15, 12, 15), (13, 13), True)
out["farm"] = g.map.farms[(13, 13)] - gather.FARM_FOOD
print(json.dumps(out))
'''


def test_toolworking_leather_armor_infantry_and_domestication_have_their_effects():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    club, bow = (out["before"][n] for n in ("CLUBMAN", "BOWMAN"))
    after = out["after"]["CLUBMAN"]
    assert after["attack"] > club["attack"] and after["melee"] > club["melee"]
    assert {k: v for k, v in after.items() if k not in ("attack", "melee")} == \
        {k: v for k, v in club.items() if k not in ("attack", "melee")}
    assert out["after"]["BOWMAN"] == bow                                # no melee unit, no infantry
    assert out["farm"] > 0
