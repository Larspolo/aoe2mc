"""The data mod in the game program (#5669, epic #5352): a game that reads a mod folder plays its values, a game with no
mod plays the AoE2 values. The modules read their data at import time, so each game runs in a new process."""
import json
import os
import subprocess
import sys

import table

GAME = os.path.dirname(table.DIR)
ROOT = os.path.dirname(GAME)
UNIT = table.read(os.path.join(table.DIR, "units.jsonl"))[0]          # the names and values come from the data files
TRAIN = table.read(os.path.join(table.DIR, "train.jsonl"))[0]
CODE = """
import json, sys
import combat, train
name, item = sys.argv[1:]
s = combat.stats(name)
print(json.dumps({"hp": s.hp, "attack": s.attack, "cost": train.COSTS[item], "time": train.TRAIN_TIMES[item]}))
"""


def mod(tmp_path):
    """A mod folder: one line of the unit and one line of the train item, each value + 1."""
    (tmp_path / "units.jsonl").write_text(json.dumps({"name": UNIT["name"], "hp": UNIT["hp"] + 1,
                                                       "attack": UNIT["attack"] + 1}) + "\n", encoding="utf-8")
    cost = {k: v + 1 for k, v in TRAIN["cost"].items()}
    (tmp_path / "train.jsonl").write_text(json.dumps({"name": TRAIN["name"], "cost": cost,
                                                       "time": TRAIN["time"] + 1}) + "\n", encoding="utf-8")
    return str(tmp_path)


def play(data_mod=None):
    """The values that a new game process uses for the unit and the train item."""
    env = {k: v for k, v in os.environ.items() if k != "AOE2MC_DATA_MOD"}
    env["PYTHONPATH"] = os.pathsep.join([ROOT, GAME])   # the game modules import the converter by name (conftest.py)
    if data_mod:
        env["AOE2MC_DATA_MOD"] = data_mod
    out = subprocess.run([sys.executable, "-c", CODE, UNIT["name"], TRAIN["name"]], cwd=GAME, env=env,
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_mod_folder_changes_the_played_values(tmp_path):
    got = play(mod(tmp_path))
    assert got["hp"] == UNIT["hp"] + 1
    assert got["attack"] == UNIT["attack"] + 1
    assert got["cost"] == {k: v + 1 for k, v in TRAIN["cost"].items()}
    assert got["time"] == TRAIN["time"] + 1


def test_no_mod_plays_the_data_values():
    got = play()
    assert got["hp"] == UNIT["hp"]
    assert got["attack"] == UNIT["attack"]
    assert got["cost"] == TRAIN["cost"]
    assert got["time"] == TRAIN["time"]
