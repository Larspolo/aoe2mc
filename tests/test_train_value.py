"""game/train.py: the keys of game/data/train.jsonl that train.value() reads have their line in
game/data/train_keys.jsonl, and BY_KEY holds their values (#2507), as civs.value (#2281). A new key of a technology then
needs no new table of game/train.py, so parallel tickets do not conflict there."""
import glob
import os
import re

import pytest

from game import table, train

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = "".join(open(f, encoding="utf-8").read() for f in sorted(glob.glob(os.path.join(ROOT, "game", "*.py"))))


def test_each_key_that_the_code_reads_with_value_has_its_description():
    own = open(os.path.join(ROOT, "game", "train.py"), encoding="utf-8").read()
    used = set(re.findall(r"""train\.value\(["'](\w+)["']""", CODE) + re.findall(r"""[^.\w]value\(["'](\w+)["']""", own))
    used |= set(re.findall(r"""BY_KEY\[["'](\w+)["']\]""", own))
    assert used and sorted(used - set(train.KEYS)) == [], "give each key its line in game/data/train_keys.jsonl"
    keys = {k for rules in ("aoe2", "antiquity") for r in table.load("train.jsonl", rules=rules) for k in r}
    assert set(train.KEYS) <= keys                     # each line names a key of train.jsonl (of a rule set: age_times, #3713)


def test_value_reads_a_key_and_gives_the_default_for_an_item_without_it():
    row = next(r for r in train.ROWS if "after" in r and "age" in r)
    assert train.value("after", row["name"]) == row["after"] and train.value("age", row["name"]) == row["age"]
    assert train.value("after", "VILLAGER_MALE", "") == "" and train.value("faster", "VILLAGER_MALE", (9, 0)) == (9, 0)
    with pytest.raises(AssertionError):
        train.value("aftre", row["name"])                              # a misspelled key


def test_the_simple_key_tables_are_gone():
    for name in ("AFTER", "CIV_TECHS", "EFFECTS", "FASTER", "SPEEDS", "TECH_AGE", "TOWER_UPGRADES", "WALL_UPGRADES"):
        assert not hasattr(train, name), name
