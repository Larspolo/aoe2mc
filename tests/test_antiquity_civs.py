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
    assert "EGYPTIANS" in antiquity["choices"] and antiquity["egyptians"] == {"1": "EGYPTIANS"}                      # JSON keys are strings
    assert antiquity["britons"] == "no choice"
    with pytest.raises(SystemExit):
        run.civ_choices(["1=EGYPTIANS"])                                    # the AoE2 rule set of this process


def test_an_economic_bonus_works_in_antiquity_mode(antiquity):
    assert all(v > 200 for v in antiquity["start"].values())               # Carthaginians: more of all resources
    babylonian, roman = antiquity["stone"]
    assert babylonian > roman                                               # Babylonian stone miners are faster


def test_a_military_bonus_works_in_antiquity_mode(antiquity):
    hittite, roman = antiquity["attack"]
    assert hittite > roman                                                  # Hittites: all archers more attack


def test_each_line_has_the_wiki_texts():
    rows = table.load("civs.jsonl", rules="antiquity")
    assert all(r["texts"]["bonuses"] and r["texts"]["team"] for r in rows)
