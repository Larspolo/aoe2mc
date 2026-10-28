"""The workflows of GitHub must parse: a `#` in an `if:` expression is text, not a comment (#3463)."""

import glob

import yaml


def test_no_comment_in_an_if_expression():
    bad = []
    for path in glob.glob(".github/workflows/*.yml"):
        with open(path) as f:
            flow = yaml.safe_load(f)
        for name, job in (flow.get("jobs") or {}).items():
            cond = job.get("if")
            if isinstance(cond, str) and "#" in cond:
                bad.append(f"{path}: job {name}")
    assert bad == []
