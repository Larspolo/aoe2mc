"""Logistics of Antiquity Mode (#3918): after it, each Barracks unit takes less population, as in Return of Rome."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import train
train.CENSUS = 1e9                                                 # the fake server has no positions of new units
out = {}
for techs in ((), ("LOGISTICS",)):
    server, g = setup(food=1000, age=0)
    g.techs.update(techs)
    g.pop = train.limit(g) - 10                                    # room for 10 population
    n = 0
    for _ in range(40):
        g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
        if not g.queues.get((16, 19, 2, 5)):
            train.queue(g, "Steve", (17, 3), "CLUBMAN")
        n += len(train.tick(g, 100))
    out[" ".join(techs) or "none"] = n
print(json.dumps(out))
'''


def test_logistics_lowers_the_population_of_barracks_units():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["LOGISTICS"] > out["none"] > 0                         # the same room holds more units
