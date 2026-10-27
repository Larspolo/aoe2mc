"""No test pins the number of entries of a data table (owner, #2008): each ticket that adds a line changes that number,
so two parallel tickets conflict on the same test line, and the count tests nothing real. Test the values instead."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNT = re.compile(r"len\((?:combat|civs|train|build|buildings|units|table)\.[A-Z][A-Z_0-9]*\) *(?:==|>=) *\d"
                   r"|len\((?:combat|civs|train|build|buildings|units|table)\.(?!ROWS\))[A-Z][A-Z_0-9]*\) *[-+] *(?:[2-9]|\d\d)")
# The second form: the length of the build menu less 4 (the hidden regional buildings) changed in 3 PRs on 2026-10-27.
# Allowed: "- 1" (the last index changes with the data) and civs.ROWS (only a new civilization adds a line).


def test_no_test_pins_the_length_of_a_table():
    bad = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.endswith(".py"):
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                bad += [f"{name}:{i}" for i, line in enumerate(f, 1) if COUNT.search(line)]
    assert not bad, f"a test pins the length of a table (#2008): {bad}"


# A literal value of a train.jsonl line (#2182): tests/test_data_files.py checks the form, the wiki gives the value.
COPY = re.compile(r"train\.(?:COSTS|TRAIN_TIMES|TECH_AGE)\[[^\]]*\] *== *[\d{]")


def test_no_test_copies_a_value_of_train_jsonl():
    bad = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.endswith(".py"):
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                bad += [f"{name}:{i}" for i, line in enumerate(f, 1) if COPY.search(line)]
    assert not bad, f"a test copies a cost, a train time or an age of train.jsonl (#2182): {bad}"
