"""The Return of Rome technologies of Antiquity Mode (#3714, docs/research/antiquity.md, 1.5): each technology of the
table in its building, age, cost and time, and the effects of Toolworking, Leather Armor Infantry and Domestication.
The rule modules read their data at import, so the checks run in one child process."""
import json
import re

from test_antiquity_setting import child

from game import table

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
AGES = {"Tool": 1, "Bronze": 2, "Iron": 3}
RES = {"food", "wood", "gold", "stone"}
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


def table_rows():
    """The rows of the technology table of section 1.5: name, building, age, cost, time."""
    text = (ROOT / "docs/research/antiquity.md").read_text().split("### 1.5")[1].split("###")[0]
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 7 and cells[2] in ("Town Center", "Market", "Storage Pit", "Government Center", "Temple"):
            cost = {r: int(n) for n, r in re.findall(r"(\d+) (\w+)", cells[4])}
            yield cells[0].upper().replace(" ", "_"), cells[2].upper().replace(" ", "_"), AGES[cells[3]], cost, int(cells[5][:-2])


def test_each_technology_of_the_table_is_in_its_building_age_cost_and_time():
    rows = {r["name"]: r for r in table.load("train.jsonl", rules="antiquity")}
    techs = list(table_rows())
    assert len(techs) == 46
    for name, building, age, cost, time in techs:
        r = rows[name]
        assert (r["building"], r["age"], r["cost"], r["time"]) == (building, age, cost, time), name
        assert set(r["cost"]) <= RES and "effect" in r, name


def test_toolworking_leather_armor_infantry_and_domestication_have_their_effects():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    club, bow = (out["before"][n] for n in ("CLUBMAN", "BOWMAN"))
    assert out["after"]["CLUBMAN"] == club | {"attack": club["attack"] + 2, "melee": club["melee"] + 2}
    assert out["after"]["BOWMAN"] == bow                                # no melee unit, no infantry
    assert out["farm"] == 75
