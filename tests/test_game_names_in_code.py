"""Game data goes in data files, not in the code (#1909): tools/data_lint.py and its list of the places left."""
import ast

import data_lint

KNOWN = {"ARCHER", "CROSSBOWMAN", "MONK", "VILLAGER"}


def test_the_code_has_no_new_game_data():
    found = {p: len(v) for p, v in data_lint.scan().items()}
    errors = data_lint.problems(found, data_lint.read())
    assert not errors, "\n".join(errors)


def test_a_literal_with_two_names_is_game_data_whatever_its_size():
    tree = ast.parse('A = ("ARCHER", "CROSSBOWMAN")\nB = ("ARCHER",)\nC = ("ARCHER", "text")\n'
                     'T = {"x": ("MONK", "VILLAGER"), "y": ("ARCHER", "MONK")}\n'
                     'def f(n):\n    return n in {"MONK": 1, "VILLAGER": 2} or n in ["ARCHER", "MONK"]\n'
                     'class K:\n    def g(self):\n        return ("MONK", "VILLAGER")\n')
    found = data_lint.literals(tree, KNOWN)
    assert {s: len(v) for s, v in found.items()} == {"A": 1, "T": 1, "f": 2, "K.g": 1}   # one count for table T
    assert found["A"] == [(1, ["ARCHER", "CROSSBOWMAN"])]


def test_the_list_only_gets_shorter():
    rows = [("a.py:X", 2), ("a.py:Y", 1)]
    assert data_lint.problems({"a.py:X": 2, "a.py:Y": 1}, rows) == []
    assert data_lint.problems({"a.py:X": 3, "a.py:Y": 1}, rows)[0].startswith("a.py:X: 3 literal(s)")     # one more
    assert data_lint.problems({"a.py:X": 2, "a.py:Y": 1, "b.py:Z": 1}, rows)[0].startswith("b.py:Z")      # a new place
    assert data_lint.problems({"a.py:X": 1, "a.py:Y": 1}, rows) == [                                       # one less
        "a.py:X: the list says 2, the code has 1: run python3 tools/data_lint.py --shrink"]


def test_a_union_merge_that_keeps_both_lines_fails():
    rows = [("a.py:X", 2), ("a.py:X", 1)]
    assert data_lint.problems({"a.py:X": 1}, rows)[0].startswith("a.py:X: two lines")


def test_shrink_lowers_and_removes_but_never_adds():
    rows = [("a.py:X", 3), ("a.py:Y", 1), ("a.py:X", 2)]
    assert data_lint.shrink({"a.py:X": 5, "b.py:Z": 1}, rows) == ["a.py:X 2"]
