"""Urbanization of Antiquity Mode (#3919, docs/research/antiquity.md 1.5): after the research each house gives double
population, the town center gives the same. The rule modules read their data at import, so the check runs in a child
process."""
import json

from test_antiquity_setting import child

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import train
server, g = setup(food=1000, age=2)
g.pop_limit = 200
base = train.limit(g)
g.sites += [{"name": "HOUSE", "player": g.player, "done": True} for _ in range(3)]
before = train.limit(g)
g.techs.add("URBANIZATION")
print(json.dumps([base, before, train.limit(g), train.HOUSING["HOUSE"]]))
'''


def test_urbanization_doubles_the_room_of_the_houses_not_of_the_town_center():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    base, before, after, house = json.loads(r.stdout.splitlines()[-1])
    assert before == base + 3 * house
    assert after == base + 3 * 2 * house
