"""The Return of Rome siege units, priests, ships and trade carts of Antiquity Mode (#3713, docs/research/antiquity.md,
1.4): each unit of the Siege Workshop, Temple, Dock and Market in its age, a Dock that trains faster in each age, and an
upgrade of a ship line. The rule modules read their data at import, so the checks run in one child process."""
import json

from test_antiquity_setting import child

from game import table

AGES = {0: ["FISHING_BOAT"], 1: ["LIGHT_TRANSPORT", "SCOUT_SHIP"], 2: ["PRIEST", "STONE_THROWER", "TRADE_BOAT", "TRADE_CART"],
        3: ["BALLISTA", "CATAPULT_TRIREME", "FIRE_GALLEY"]}
CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import combat, train
out = {"open": {}, "times": {}}
server, g = setup(food=1000, age=0)
for i, age in enumerate(["", "TOOL_AGE", "BRONZE_AGE", "IRON_AGE"]):
    g.techs.add(age) if age else None
    out["open"][i] = sorted(n for b in ("DOCK", "MARKET", "SIEGE_WORKSHOP", "TEMPLE") for n in train.TRAINS[b]
                            if train.unlocked(g, n) and n not in train.UPGRADES)
    out["times"][i] = [train.seconds(g, n, "DOCK") for n in ("SCOUT_SHIP", "WAR_GALLEY_UPGRADE")]
    if i == 2:                                                         # the Bronze Age: Scout Ship to War Galley
        g.soldiers["x"] = "SCOUT_SHIP"
        train.research(g, {"name": "WAR_GALLEY_UPGRADE", "player": "Steve"})
        out["upgraded"] = g.soldiers["x"]
        out["dock"] = list(train.trains(g, "DOCK"))
out["galley"] = combat.stats("WAR_GALLEY")._asdict()
out["villager"] = train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER")
print(json.dumps(out))
'''


def test_the_buildings_train_each_age_the_dock_trains_faster_and_a_ship_line_upgrades():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    seen = []
    for age, names in AGES.items():
        seen = sorted(seen + names)
        assert out["open"][str(age)] == seen, age
    assert [t[0] for t in out["times"].values()] == [70, 46, 41, 35]   # the Scout Ship: Tool 46 s, Iron 35 s (wiki "Time")
    assert out["times"]["3"][1] == 64                                  # the War Galley upgrade in the Iron Age
    assert out["upgraded"] == "WAR_GALLEY"
    assert "WAR_GALLEY" in out["dock"] and "SCOUT_SHIP" not in out["dock"]
    assert out["galley"]["hp"] == 160 and out["galley"]["attack"] == 8 and out["galley"]["range"] == 6
    assert out["villager"] == 20                                       # no "age_times": the plain time


def test_each_new_unit_has_values_a_mob_and_each_upgrade_a_known_unit():
    import units
    values = {r["name"] for r in table.load("units.jsonl", rules="antiquity")}
    rows = {r["name"]: r for r in table.load("train.jsonl", rules="antiquity")}
    new = [n for n, r in rows.items() if "#3713" in r.get("note", "") and "upgrade" not in r]
    assert len(new) == 19 and set(new) <= values
    assert all(units.classify(n)["id"] != "minecraft:zombie" for n in new), new
    assert all(set(r["upgrade"]) <= set(new) for r in rows.values() if "#3713" in r.get("note", "") and "upgrade" in r)


def test_the_aoe2_dock_has_no_age_times():
    assert not any("age_times" in r for r in table.load("train.jsonl", rules="aoe2"))
