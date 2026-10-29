"""The Return of Rome civilizations of Antiquity Mode (#3667, docs/research/antiquity.md, 1.1): game/data/antiquity/civs.jsonl
replaces the AoE2 list, so each one is a --civ choice only with --antiquity. The behaviour checks run in one child
process with AOE2MC_RULES=antiquity (2.3, step 4)."""
import json
import os
import subprocess
import sys

import pytest

from game import run, table

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game")
CIVS = ["ASSYRIANS", "BABYLONIANS", "CARTHAGINIANS", "CHOSON", "EGYPTIANS", "GREEKS", "HITTITES", "LAC_VIET",
        "MACEDONIANS", "MINOANS", "PALMYRANS", "PERSIANS", "PHOENICIANS", "ROMANS", "SHANG", "SUMERIANS", "YAMATO"]
CODE = f"""
import json, sys, types
sys.path.insert(0, {GAME!r})
import run, civs, train
g = lambda civ: types.SimpleNamespace(data={{"players": {{"1": {{"civ": civ}}}}}}, player=1, techs=set())
out = {{"choices": sorted(r["name"] for r in civs.ROWS), "egyptians": run.civ_choices(["1=egyptians"]),
       "start": civs.start(g("CARTHAGINIANS"), {{"food": 200, "wood": 200}}),
       "stone": [civs.work(g(c), "stone") for c in ("BABYLONIANS", "ROMANS")],
       "attack": [train.stats(g(c), "ARCHER").attack for c in ("HITTITES", "ROMANS")]}}
try:
    run.civ_choices(["1=BRITONS"])
except SystemExit:
    out["britons"] = "no choice"
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def antiquity():
    env = dict(os.environ, AOE2MC_RULES="antiquity")
    return json.loads(subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True, env=env,
                                     check=True).stdout)


def test_each_return_of_rome_civilization_is_a_choice_only_in_antiquity_mode(antiquity):
    assert antiquity["choices"] == CIVS
    assert antiquity["egyptians"] == {"1": "EGYPTIANS"}                      # JSON keys are strings
    assert antiquity["britons"] == "no choice"
    with pytest.raises(SystemExit):
        run.civ_choices(["1=EGYPTIANS"])                                    # the AoE2 rule set of this process


def test_an_economic_bonus_works_in_antiquity_mode(antiquity):
    assert antiquity["start"] == {"food": 250, "wood": 250}                 # Carthaginians: +50 of all resources
    assert antiquity["stone"] == [1.2, 1]                                   # Babylonian stone miners 20 % faster


def test_a_military_bonus_works_in_antiquity_mode(antiquity):
    hittite, roman = antiquity["attack"]
    assert hittite == roman + 1                                             # Hittites: all archers +1 attack


def test_each_line_has_the_wiki_texts():
    rows = table.load("civs.jsonl", rules="antiquity")
    assert [r["name"] for r in rows] == CIVS
    assert all(r["texts"]["bonuses"] and r["texts"]["team"] for r in rows)
