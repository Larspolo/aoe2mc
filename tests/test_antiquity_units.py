"""The Return of Rome land units of Antiquity Mode (#3669, docs/research/antiquity.md, 1.4): each unit of the
Barracks, Archery Range, Stable and Academy in its age with the values of the wiki, an upgrade of a unit line, and the
damage of a fight. The rule modules read their data at import, so the checks run in one child process."""
import json

from test_antiquity_setting import child

from game import table

AGES = {0: ["CLUBMAN"], 1: ["BOWMAN", "SCOUT", "SLINGER"],
        2: ["CAMEL_RIDER", "CAVALRY", "CHARIOT", "CHARIOT_ARCHER", "HOPLITE", "IMPROVED_BOWMAN", "SHORT_SWORDSMAN"],
        3: ["ELEPHANT_ARCHER", "HORSE_ARCHER", "WAR_ELEPHANT"]}
CODE = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from test_forging import setup
import combat, train
out = {"open": {}, "trains": {}}
server, g = setup(food=1000, age=0)
g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
for i, age in enumerate(["", "TOOL_AGE", "BRONZE_AGE", "IRON_AGE"]):
    g.techs.add(age) if age else None
    out["open"][i] = sorted(n for b in ("ACADEMY", "ARCHERY_RANGE", "BARRACKS", "STABLE") for n in train.TRAINS[b]
                            if train.unlocked(g, n) and n not in train.UPGRADES)
    if i == 0:                                                         # the Stone Age: train a clubman
        rect = train.open_menu(g, "Steve", (17, 3))
        assert train.order(g, "Steve", rect, 0) == 1
        before = set(g.soldiers)
        train.tick(g, train.TRAIN_TIMES["CLUBMAN"] + 1)
        out["trained"] = sorted(g.soldiers[u] for u in set(g.soldiers) - before)
    if i == 1:                                                         # the Tool Age: Clubman to Axeman
        g.soldiers["m"] = "CLUBMAN"
        rect = train.open_menu(g, "Steve", (17, 3))
        assert train.order(g, "Steve", rect, 3) == 1
        train.tick(g, train.TRAIN_TIMES["AXEMAN_UPGRADE"] + 1)
        out["upgraded"] = g.soldiers["m"]
        out["barracks"] = list(train.trains(g, "BARRACKS"))
out["damage"] = {f"{a} {t}": combat.damage(a, t) for a, t in [("AXEMAN", "SHORT_SWORDSMAN"), ("CAMEL_RIDER", "CAVALRY"),
                                                             ("CLUBMAN", "HOPLITE"), ("SLINGER", "BOWMAN")]}
out["hoplite"] = combat.stats("HOPLITE")._asdict()
print(json.dumps(out))
'''


def test_the_buildings_train_the_units_of_each_age_and_upgrade_a_line():
    r = child(CODE)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    seen = []
    for age, names in AGES.items():
        seen = sorted(seen + names)
        assert out["open"][str(age)] == seen, age
    assert out["trained"] == ["CLUBMAN"]
    assert out["upgraded"] == "AXEMAN"
    assert "AXEMAN" in out["barracks"] and "CLUBMAN" not in out["barracks"]
    assert out["damage"] == {"AXEMAN SHORT_SWORDSMAN": 4,                # 5 attack - 1 melee armor
                             "CAMEL_RIDER CAVALRY": 14,                  # 6 + 8 vs. cavalry
                             "CLUBMAN HOPLITE": 1,                       # 3 - 5: the least damage
                             "SLINGER BOWMAN": 5}                        # 2 + 3 vs. archers
    assert out["hoplite"]["hp"] == 120 and out["hoplite"]["melee"] == 5


def test_each_unit_has_values_and_each_upgrade_a_known_unit():
    values = {r["name"] for r in table.load("units.jsonl", rules="antiquity")}
    rows = table.load("train.jsonl", rules="antiquity")
    units = {r["name"] for r in rows if r.get("item") not in (None, "bell", "book") and r["name"] != "VILLAGER_MALE"}
    assert len(units) == 45 and units <= values
    assert all(set(r["upgrade"]) <= units for r in rows if "upgrade" in r)
