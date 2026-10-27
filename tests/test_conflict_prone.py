"""No test pins the number of entries of a data table (owner, #2008): each ticket that adds a line changes that number,
so two parallel tickets conflict on the same test line, and the count tests nothing real. Test the values instead."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNT = re.compile(r"len\((?:combat|civs|train|build|buildings|units|table)\.[A-Z][A-Z_0-9]*\) *== *\d")


def test_no_test_pins_the_length_of_a_table():
    bad = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.endswith(".py"):
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                bad += [f"{name}:{i}" for i, line in enumerate(f, 1) if COUNT.search(line)]
    assert not bad, f"a test pins the length of a table (#2008): {bad}"
