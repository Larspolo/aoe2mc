"""An `if:` expression of a workflow has no `#` outside a quoted string (#3466): a comment line inside a folded
`if: >-` block stays in the expression, and GitHub refuses the whole file (Automerge stopped after #3436)."""
import glob
import os
import re

import yaml

WORKFLOWS = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows")


def conditions(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "if" and isinstance(value, str):
                yield path, value
            yield from conditions(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from conditions(value, f"{path}/{i}")


def test_no_comment_in_an_if_expression():
    bad = []
    for name in sorted(glob.glob(os.path.join(WORKFLOWS, "*.yml"))):
        for path, expr in conditions(yaml.safe_load(open(name))):
            if "#" in re.sub(r"'(?:[^']|'')*'", "", expr):
                bad.append(f"{os.path.basename(name)}{path}: {expr}")
    assert not bad, bad


def test_the_check_finds_a_comment_line_in_a_folded_if():
    text = "jobs:\n  a:\n    if: >-\n      github.event_name == 'push'\n      # a comment\n    steps: []\n"
    assert [p for p, e in conditions(yaml.safe_load(text)) if "#" in re.sub(r"'(?:[^']|'')*'", "", e)] == ["/jobs/a"]
