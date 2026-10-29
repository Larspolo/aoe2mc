"""Theocracy in Antiquity Mode (#3989): the Priest of Antiquity Mode is a monk for the conversion rules, so Theocracy
works for it as for the AoE2 monks (tests/test_theocracy.py). Before Theocracy, all priests that convert one unit rest;
after it, only the one that converts it. The rule modules read their data at import, so the check runs in one child
process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_gather import FakeServer, grid
from game import gather, monk

def group(*techs):
    """Three own priests next to each other and two enemy militia 7 tiles away: all three priests convert the first one."""
    objects = [{"kind": "unit", "name": "PRIEST", "player": 1, "uuid": f"m{i}", "tile": [5.5, 5.5 + i]} for i in range(3)]
    objects += [{"kind": "unit", "name": "MILITIA", "player": 2, "uuid": f"foe{i}", "tile": [12.5, 5.5 + i]}
                for i in range(2)]
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects}
    g = gather.Gather(FakeServer(ents), grid([[64] * 40 for _ in range(40)], objects)).setup()
    g.techs |= set(techs)
    assert monk.convert_order(g, {"m0", "m1", "m2"}, "foe0")
    t = 0.0
    while "foe0" in g.enemies and t < 20:
        monk.convert(g, 0.25)
        t += 0.25
    assert "foe0" in g.soldiers and not g.converting
    return g

out = {}
g = group()
out["without"] = {"resting": sorted(g.faith), "all_rest": all(f > monk.REST - 1 for f in g.faith.values())}
assert monk.convert_order(g, {"m1"}, "foe1")
monk.convert(g, 0.25)
out["without"]["chant_m1"] = g.converting["m1"][1]
g = group("THEOCRACY")
out["with"] = {"resting": sorted(g.faith), "rest": list(g.faith.values())[0] > monk.REST - 1}
free = sorted({"m0", "m1", "m2"} - set(g.faith))[0]
assert monk.convert_order(g, {free}, "foe1")
monk.convert(g, 0.25)
out["with"]["free"] = free
out["with"]["chant_free"] = g.converting[free][1]
print(json.dumps(out))
'''


def test_theocracy_leaves_one_priest_resting_in_antiquity_mode():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert len(out["without"]["resting"]) == 3 and out["without"]["all_rest"]
    assert out["without"]["chant_m1"] == 0, "it rests: no chant"
    assert len(out["with"]["resting"]) == 1 and out["with"]["rest"]
    assert out["with"]["chant_free"] > 0, "it chants at once"
