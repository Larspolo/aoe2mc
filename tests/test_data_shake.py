"""tools/data_shake.py finds a test that checks a named value of the unit data (#5388)."""
import json
import os

import numpy as np

from tools import data_shake

FAKE = '''
from game import combat


def test_named():
    assert combat.stats("MILITIA").hp == %d


def test_from_the_data():
    assert combat.stats("MILITIA").hp > 0


def test_fails_always():
    assert False
'''


def test_a_named_value_fails_and_a_relation_passes(tmp_path):
    hp = json.loads(open(os.path.join(data_shake.DATA, "units.jsonl")).readline())["hp"]
    f = tmp_path / "test_fake.py"
    f.write_text(FAKE % hp)
    assert data_shake.failed([str(f)]) == {"test_fake::test_fails_always"}
    assert data_shake.main([str(f)]) == 1
    mod = tmp_path / "mod"
    data_shake.main([str(f), "--keep", str(mod)])
    assert data_shake.failed([str(f)], str(mod)) == {"test_fake::test_named", "test_fake::test_fails_always"}


def test_the_lines_keep_their_form():
    rng = np.random.default_rng(0)
    rows = [{"name": "A", "hp": 40, "attack": 4, "melee": -2, "range": 0, "reload": 2.0, "bonus": {"x": 5, "y": 3},
             "classes": ["infantry"]}]
    (line,) = data_shake.shake(rows, rng, drop=0)
    assert line["name"] == "A" and "classes" not in line
    assert line["hp"] > 40 and line["attack"] > 4 and line["melee"] < -2 and line["range"] == 0
    assert isinstance(line["hp"], int) and isinstance(line["reload"], float) and line["reload"] > 2.0
    assert set(line["bonus"]) == {"x", "y"} and line["bonus"]["x"] > 5
    assert data_shake.shake(rows, np.random.default_rng(0), drop=1)[0]["bonus"] == {}
