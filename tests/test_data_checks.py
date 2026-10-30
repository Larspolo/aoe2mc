"""The checks of tests/data_checks/ find the same errors as the old checks of tests/test_data_files.py (#4778): a line
of test data with one bad value fails, the line of the data file passes. Each module of the directory is found with no
list."""
import os

import data_checks
import pytest
from data_checks import rows
from test_data_files import CHECKS


def first(name, key=None):
    """A copy of the first line of data file name (with key, when given)."""
    return dict(next(r for r in rows(name) if key is None or key in r))


def test_each_module_of_the_directory_is_a_check_of_its_data_file():
    here = os.path.dirname(data_checks.__file__)
    mods = {f[:-3] for f in os.listdir(here) if f.endswith(".py") and f != "__init__.py"}
    assert {f"{m}.jsonl" for m in mods} == set(CHECKS) and all(callable(m.check) for m in CHECKS.values())


@pytest.mark.parametrize("name, key, bad", [
    ("units.jsonl", "hp", "10"),                           # a wrong type of a key of all units
    ("units.jsonl", "on_death", "NO_SUCH_UNIT"),           # a name that no line has
    ("train.jsonl", "building", "NO_SUCH_BUILDING"),
    ("train.jsonl", "cost", {"iron": 1}),                  # no resource
    ("civs.jsonl", "unique", "NO_SUCH_UNIT"),
    ("challenges.jsonl", "civ", "NO_SUCH_CIV"),
    ("per_names.jsonl", "kind", "no_such_kind"),
    ("civ_keys.jsonl", "issue", 0),
    ("train_keys.jsonl", "text", ""),                      # the check of civ_keys.jsonl
])
def test_a_line_with_a_bad_value_fails_and_the_line_of_the_data_passes(name, key, bad):
    row = first(name, key)
    CHECKS[name].check(row)
    with pytest.raises(AssertionError):
        CHECKS[name].check({**row, key: bad})


def test_a_line_with_no_key_of_need_fails():
    row = first("units.jsonl")
    del row["attack"]
    with pytest.raises(AssertionError, match="attack"):
        CHECKS["units.jsonl"].check(row)

