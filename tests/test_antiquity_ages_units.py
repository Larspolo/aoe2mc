"""Antiquity Mode, one unit in each age (#3664, criterion 3): a player trains a unit of the Stone, Tool, Bronze and
Iron Age and advances to the next age between them. The plan (the advances and the units) comes from the data
(game/data/antiquity/train.jsonl), not from a list here. The rule modules read their data at import, so the checks
run in one child process (test_antiquity_setting.child)."""
import json

from test_antiquity_setting import child

from game import table

ROWS = table.load("train.jsonl", rules="antiquity")
BY = {r["name"]: r for r in ROWS}
ADVANCES = ["TOOL_AGE", "BRONZE_AGE", "IRON_AGE"]                       # the advance into each age after the Stone Age
MILITARY = ("BARRACKS", "ARCHERY_RANGE", "STABLE", "ACADEMY")          # buildings that train soldiers
CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from menu_line import item
from test_feudal_age import add
from test_loom import menus, setup
import train
server, g = setup(food=2300, gold=800)
g.stock.update(food=5000, wood=5000, gold=5000, stone=5000)           # the units of all ages cost more than the advances
rect = train.open_menu(g, "Steve", (3, 3))
out = {"start": train.age(g), "ages": [], "trained": []}
for key, label, reqs, unit, unit_label, building in json.loads(sys.argv[1]):
    if key:                                                            # advance to the age (as in AGES)
        g.data["objects"] = [o for o in g.data["objects"] if o["kind"] != "building" or o["name"] == "TOWN_CENTER"]
        add(g, *reqs)
        seconds = train.seconds(g, key, "TOWN_CENTER")
        train.show(g, "Steve", rect)
        train.order(g, "Steve", rect, int(item(menus(server)[-1], label).split(":")[0]))
        train.tick(g, seconds - 1)
        train.tick(g, 1)
    out["ages"].append(train.age(g))
    g.data["objects"] = [o for o in g.data["objects"] if o["kind"] != "building" or o["name"] == "TOWN_CENTER"]
    add(g, building, "HOUSE", "HOUSE")                                 # one complete building of the unit's age, and room
    unit_rect = train.open_menu(g, "Steve", (12, 2))
    train.show(g, "Steve", unit_rect)
    queued = train.order(g, "Steve", unit_rect, int(item(menus(server)[-1], unit_label).split(":")[0]))
    before = set(g.soldiers)
    train.tick(g, train.seconds(g, unit, building) + 1)
    out["trained"].append([queued, sorted(g.soldiers[u] for u in set(g.soldiers) - before)])
print(json.dumps(out))
'''


def plan():
    """Per age: the advance into it (None in the Stone Age) and one unit of that age, from the data (#3669)."""
    values = {r["name"] for r in table.load("units.jsonl", rules="antiquity")}
    out = []
    for age in range(4):
        unit = next(r for r in ROWS if r.get("age", 0) == age and r.get("building") in MILITARY
                    and "upgrade" not in r and r["name"] in values)
        advance = [None, None, None] if age == 0 else [ADVANCES[age - 1], BY[ADVANCES[age - 1]]["label"],
                                                        BY[ADVANCES[age - 1]]["requires"][1][:2]]
        out.append([*advance, unit["name"], unit["label"], unit["building"]])
    return out


def test_a_unit_of_each_age_trains_and_the_player_advances_to_the_iron_age():
    p = plan()
    r = child(CODE, json.dumps(p))
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["start"] == "Stone Age"
    assert out["ages"] == ["Stone Age", "Tool Age", "Bronze Age", "Iron Age"]
    assert out["trained"] == [[1, [row[3]]] for row in p]              # one new unit of each age
