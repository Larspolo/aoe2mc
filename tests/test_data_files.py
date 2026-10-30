"""The data files of the game program have the right form (#1916): each line is JSON, the names are unique, the keys
and the value types are the expected ones, and each name that a line refers to exists. A new data line needs no test
of its values: the values come from the AoE2 wiki, and this file checks their form. The check of each file is its
module in tests/data_checks/ (#4778): this file has no line per data file or per key."""
import importlib
import json
import os
import pkgutil

import data_checks
import pytest
from data_checks import NAMES, rows

from game import table

CHECKS = {f"{m.name}.jsonl": importlib.import_module(f"data_checks.{m.name}") for m in pkgutil.iter_modules(data_checks.__path__)}


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_key_has_one_type(name):
    two = getattr(CHECKS.get(name), "TWO_TYPES", {})     # the keys with two types by design, in the module of the file
    types = {}
    for row in rows(name):
        for k, v in row.items():
            if k in two:
                assert isinstance(v, two[k]), (name, row["name"], k)
                continue
            t = float if type(v) is int else type(v)       # an int is a float without a fraction; null: none
            assert v is None or types.setdefault(k, t) is t, (name, row["name"], k)


def test_the_effect_name_of_a_technology_is_a_function_of_train():
    from game import train
    for row in rows("train.jsonl"):
        assert callable(getattr(train, row.get("effect") if isinstance(row.get("effect"), str) else "effect")), row["name"]


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_line_is_one_json_object_with_a_unique_name(name):
    lines = [s for s in open(os.path.join(table.DIR, name), encoding="utf-8") if s.strip()]
    assert all(isinstance(json.loads(s), dict) for s in lines)
    assert len(rows(name)) == len(lines) == len(NAMES[name])      # table.load stops on a name in two lines


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_line_has_the_keys_and_the_names_of_its_file(name):
    assert name in CHECKS, f"give {name} its check: tests/data_checks/{name[:-len('.jsonl')]}.py with check(row)"
    for row in rows(name):
        CHECKS[name].check(row)
