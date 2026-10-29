"""The setting --antiquity (#3666, docs/research/antiquity.md, 2.3): the rule set folder game/data/antiquity, and the
four ages of Return of Rome in the town center menu. The tests of Antiquity Mode run in a child process with
AOE2MC_RULES=antiquity, because the rule modules read their data at import."""
import json
import os
import subprocess
import sys

import pytest

from game import build, train

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
for age, names, seconds in [("Tool Age", ["BARRACKS", "GRANARY"], 120), ("Bronze Age", ["MARKET", "STABLE"], 140),
                            ("Iron Age", ["ACADEMY", "TEMPLE"], 160)]:
    g.data["objects"] = [o for o in g.data["objects"] if o["kind"] != "building" or o["name"] == "TOWN_CENTER"]
    add(g, *names)                                                     # two buildings of the current age
    train.show(g, "Steve", rect)
    slot = int(item(menus(server)[-1], age).split(":")[0])
    queued = train.order(g, "Steve", rect, slot)
    train.tick(g, seconds - 1)
    early = train.age(g)
    train.tick(g, 1)
    out["ages"].append([queued, early, train.age(g), dict(g.stock),
                        any(f"Player 1 advances to the {age}." in c for c in server.log)])
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
    assert out["need"] == "2:bell:Tool Age:500 food · 120 s · needs 2 of barracks, dock, granary, storage pit (0/2)"
    stock = {"food": 2300, "gold": 800}
    ages = [("Stone Age", "Tool Age", {"food": 500}), ("Tool Age", "Bronze Age", {"food": 800}),
            ("Bronze Age", "Iron Age", {"food": 1000, "gold": 800})]
    for (queued, early, now, left, told), (before, after, cost) in zip(out["ages"], ages):
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
    assert table.load("units.jsonl", rules="antiquity") == table.load("units.jsonl")   # no own file: the AoE2 lines


def test_without_antiquity_the_ages_stay():
    assert train.AGES == ("Dark Age", "Feudal Age", "Castle Age", "Imperial Age")
    assert build.AGE_TECHS == ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


@pytest.mark.parametrize("option", ["--replay", "--mode=regicide"])
def test_antiquity_plays_only_the_standard_mode(option):
    r = child("import sys; sys.path.insert(0, 'game'); import run; run.main(sys.argv[1:])", "W", "--antiquity", option)
    assert "--antiquity plays only --mode standard" in r.stderr
