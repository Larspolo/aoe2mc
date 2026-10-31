"""The setting --antiquity (#3666, docs/research/antiquity.md, 2.3): the rule set folder game/data/antiquity, and the
four ages of Return of Rome in the town center menu. The tests of Antiquity Mode run in a child process with
AOE2MC_RULES=antiquity, because the rule modules read their data at import."""
import json
import os
import subprocess
import sys

import pytest

from game import train

table = train.table                                                     # the module that the rule modules use

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGES = r'''
import json, sys
sys.path[:0] = ["game", "tests"]
from menu_line import item
from test_feudal_age import add
from test_loom import menus, setup
import train
server, g = setup(food=2300, gold=800)
rect = train.open_menu(g, "Steve", (3, 3))
out = {"start": train.age(g), "need": item(menus(server)[-1], "Tool Age"), "ages": []}
for age, names in [("Tool Age", ["BARRACKS", "GRANARY"]), ("Bronze Age", ["MARKET", "STABLE"]),
                   ("Iron Age", ["ACADEMY", "TEMPLE"])]:
    key = age.upper().replace(" ", "_")
    cost, seconds = train.price(g, key), train.seconds(g, key, "TOWN_CENTER")
    g.data["objects"] = [o for o in g.data["objects"] if o["kind"] != "building" or o["name"] == "TOWN_CENTER"]
    add(g, *names)                                                     # two buildings of the current age
    train.show(g, "Steve", rect)
    slot = int(item(menus(server)[-1], age).split(":")[0])
    queued = train.order(g, "Steve", rect, slot)
    train.tick(g, seconds - 1)
    early = train.age(g)
    train.tick(g, 1)
    out["ages"].append([queued, early, train.age(g), dict(g.stock), cost,
                        any(f'"with": ["1", "{age}"]' in c for c in server.log)])
print(json.dumps(out))
'''


def child(code, *args):
    env = {**os.environ, "AOE2MC_RULES": "antiquity"}
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True, cwd=ROOT, env=env)


def test_a_player_advances_from_the_stone_age_to_the_iron_age():
    r = child(AGES)
    assert r.returncode == 0, r.stderr[-2000:]
    out = json.loads(r.stdout.splitlines()[-1])
    assert out["start"] == "Stone Age"
    assert ":Tool Age:" in out["need"] and " needs " in out["need"]
    stock = {"food": 2300, "gold": 800}
    ages = [("Stone Age", "Tool Age"), ("Tool Age", "Bronze Age"), ("Bronze Age", "Iron Age")]
    for (queued, early, now, left, cost, told), (before, after) in zip(out["ages"], ages):
        stock = {k: v - cost.get(k, 0) for k, v in stock.items()}
        assert (queued, early, now, told) == (1, before, after, True)
        assert {k: left[k] for k in stock} == stock


def test_the_rule_set_cannot_change_after_a_rule_file_loaded():
    assert table.RULES == "aoe2"                                        # this process: the AoE2 rules
    with pytest.raises(RuntimeError, match="train.jsonl"):
        table.use("antiquity")


def test_the_rule_set_replaces_the_item_lists_and_adds_to_the_lookups():
    names = {r["name"] for r in table.load("train.jsonl", rules="antiquity")}
    assert {"TOOL_AGE", "BRONZE_AGE", "IRON_AGE", "VILLAGER_MALE"} <= names and "FEUDAL_AGE" not in names
    old, new = ({r["name"]: r for r in table.load("units.jsonl", **k)} for k in ({}, {"rules": "antiquity"}))
    assert set(old) < set(new) and "HOPLITE" in new and new["MILITIA"] == old["MILITIA"]   # adds, keeps the AoE2 lines
    assert new["CENTURION"] != old["CENTURION"]                                            # a line of the same name (#3669)


@pytest.mark.parametrize("option", ["--replay", "--mode=regicide"])
def test_antiquity_plays_only_the_standard_mode(option):
    r = child("import sys; sys.path.insert(0, 'game'); import run; run.main(sys.argv[1:])", "W", "--antiquity", option)
    assert "--antiquity plays only --mode standard" in r.stderr
