"""No test pins the number of entries of a data table (owner, #2008): each ticket that adds a line changes that number,
so two parallel tickets conflict on the same test line, and the count tests nothing real. No test copies a value of a
data file either (owner, 2026-10-29): test the form of the data and the behavior of the code."""
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
COPY = re.compile(r"train\.(?:COSTS|TRAIN_TIMES|BY_KEY\[\"age\"\])\[[^\]]*\] *== *[\d{]")


def test_no_test_copies_a_value_of_train_jsonl():
    bad = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.endswith(".py"):
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                bad += [f"{name}:{i}" for i, line in enumerate(f, 1) if COPY.search(line)]
    assert not bad, f"a test copies a cost, a train time or an age of train.jsonl (#2182): {bad}"


# A literal combat value of units.jsonl or buildings.jsonl (sight, a stat) or a walk speed of replay.jsonl or of a ship
# (#2223): tests/test_data_files.py checks the form, the wiki gives the value. A behavior test compares computed values.
STAT = re.compile(r"(?:combat\.sight\([^)]*\)|replay\.SPEEDS(?:\[[^\]]*\]|\.get\([^)]*\))|fleet\.SPEEDS\[[^\]]*\]"
                  r"|combat\.(?:STATS|BUILDINGS)\[[^\]]*\]\.\w+(?:\[[^\]]*\])?|combat\.stats\(\"[A-Z_]+\"\)(?:\.\w+|\[[^\]]*\])?)"
                  r" *== *\(?-?\d")


def test_no_test_copies_a_combat_value_or_a_speed():
    bad = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.endswith(".py") and name != "test_conflict_prone.py":
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                bad += [f"{name}:{i}" for i, line in enumerate(f, 1) if STAT.search(line)]
    assert not bad, f"a test copies a sight, a stat or a speed of a data file (#2223): {bad}"


def test_the_stat_lint_finds_the_copies():
    assert STAT.search('assert combat.sight("MONK") == 11') and STAT.search("replay.SPEEDS[unit] == 0.6")
    assert STAT.search('combat.stats("SAVAR") == (145, 14') and STAT.search('combat.BUILDINGS["DOCK"].hp == 1800')
    assert not STAT.search('combat.BUILDINGS["DOCK"].classes == ("building", combat.STANDARD)')
    assert not STAT.search("combat.sight(unit) == combat.sight(base) + 2")


# A literal age or cost of a build.jsonl line (#2222): the same rule for the buildings and the age of the units.
COPY_BUILD = re.compile(r"build\.(?:AGE|COSTS)\[[^\]]*\] *== *[\d{]")


def test_no_test_copies_a_value_of_build_jsonl():
    bad = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if name.endswith(".py") and name != "test_conflict_prone.py":
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                bad += [f"{name}:{i}" for i, line in enumerate(f, 1) if COPY_BUILD.search(line)]
    assert not bad, f"a test copies an age or a cost of build.jsonl (#2222): {bad}"


def test_the_build_copy_lint_finds_the_copies():
    assert COPY_BUILD.search('assert train.build.AGE["ELITE_ARAMBAI"] == 3')
    assert COPY_BUILD.search('assert gather.NOMAD == build.COSTS["TOWN_CENTER"] == {"wood": 275}')
    assert COPY_BUILD.search('assert build.AGE["A"] == build.AGE["B"] == 1')
    assert not COPY_BUILD.search('assert build.AGE["KNIGHT"] == build.AGE["CAVALRY_ARCHER"]')
