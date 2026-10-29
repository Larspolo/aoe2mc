"""The Return of Rome siege units, priests, ships and trade carts of Antiquity Mode (#3713, docs/research/antiquity.md,
1.4): each unit of the Siege Workshop, Temple, Dock and Market in its age, a Dock that trains faster in each age, and an
upgrade of a ship line. The rule modules read their data at import, so the checks run in one child process."""
import json

from test_antiquity_setting import child

from game import table

CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import train
out = {"open": {}, "times": {}}
server, g = setup(food=1000, age=0)
for i, age in enumerate(["", "TOOL_AGE", "BRONZE_AGE", "IRON_AGE"]):
    g.techs.add(age) if age else None
    out["open"][i] = sorted(n for b in ("DOCK", "MARKET", "SIEGE_WORKSHOP", "TEMPLE") for n in train.TRAINS[b]
                            if train.unlocked(g, n) and n not in train.UPGRADES and n not in train.TECHS)
    out["times"][i] = [train.seconds(g, n, "DOCK") for n in ("SCOUT_SHIP", "WAR_GALLEY_UPGRADE")]
    if i == 2:                                                         # the Bronze Age: Scout Ship to War Galley
        g.soldiers["x"] = "SCOUT_SHIP"
        train.research(g, {"name": "WAR_GALLEY_UPGRADE", "player": "Steve"})
        out["upgraded"] = g.soldiers["x"]
        out["dock"] = list(train.trains(g, "DOCK"))
out["upgrade"] = train.UPGRADES["WAR_GALLEY_UPGRADE"]
out["villager"] = [train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER"), train.TRAIN_TIMES["VILLAGER_MALE"]]
print(json.dumps(out))
'''


def test_the_buildings_train_each_age_the_dock_trains_faster_and_a_ship_line_upgrades():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    opened = [set(out["open"][str(age)]) for age in range(4)]
    assert all(a < b for a, b in zip(opened, opened[1:]))              # each age adds units
    scout = [t[0] for t in out["times"].values()]
    assert all(a > b for a, b in zip(scout, scout[1:]))                # the Scout Ship trains faster in each age
    assert out["upgrade"] == ["SCOUT_SHIP", out["upgraded"]]
    assert out["upgraded"] in out["dock"] and "SCOUT_SHIP" not in out["dock"]
    assert out["villager"][0] == out["villager"][1]                    # no "age_times": the plain time


def test_each_new_unit_has_values_a_mob_and_each_upgrade_a_known_unit():
    import units
    values = {r["name"] for r in table.load("units.jsonl", rules="antiquity")}
    rows = {r["name"]: r for r in table.load("train.jsonl", rules="antiquity")}
    new = [n for n, r in rows.items() if "#3713" in r.get("note", "") and "upgrade" not in r]
    assert new and set(new) <= values
    assert all(units.classify(n)["id"] != "minecraft:zombie" for n in new), new
    assert all(set(r["upgrade"]) <= set(new) for r in rows.values() if "#3713" in r.get("note", "") and "upgrade" in r)
