"""tools/merge_jsonl.py merges a line that both sides changed key by key: two new unique units change the "missing"
list of each civilization line, and that must not be a conflict (owner request, 2026-10-27)."""
import json

import merge_jsonl
from test_merge_jsonl import line, merged


def test_both_sides_add_to_the_missing_list():
    base, ours, theirs = ([line("AZTECS", missing=m)] for m in (["A", "D"], ["A", "B", "D"], ["A", "C", "D"]))
    lines = merge_jsonl.merge(*(merge_jsonl.rows_of(x) for x in (base, ours, theirs)))
    assert lines == ([line("AZTECS", missing=["A", "B", "C", "D"])], 0)


def test_a_remove_and_an_add_and_other_keys():
    o = line("AZTECS", missing=["A", "B"], bonus=1)
    a = line("AZTECS", missing=["B", "C"], bonus=1, unique=["X"])               # removes A, adds C and a key
    b = line("AZTECS", missing=["A", "B", "D"], bonus=2)                        # adds D, changes bonus
    assert merge_jsonl.merge_line(o, a, b) == line("AZTECS", missing=["B", "C", "D"], bonus=2, unique=["X"])
    assert merge_jsonl.merge_line(o, line("AZTECS", bonus=3), b) is None        # bonus 3 and 2: a conflict


def test_a_real_git_merge_of_two_unique_units(tmp_path):
    ours = [line("AZTECS", missing=["A", "B"]), line("BRITONS", missing=["A", "B"]), line("CELTS", missing=["A"])]
    theirs = [line("AZTECS", missing=["A", "C"]), line("BRITONS", missing=["A", "C"]), line("CELTS", missing=["A", "C"])]
    rc, lines = merged(tmp_path, ours, theirs)
    assert rc == 0
    assert [json.loads(x)["missing"] for x in lines] == [["A", "B", "C"], ["A", "B", "C"], ["A", "C"]]
