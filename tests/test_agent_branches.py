"""Each place that names the branches of agent PRs names the same prefixes (#3382): agent/, claude/ and the ccr- of
owner sessions."""
import re
from pathlib import Path

import operator_check
import test_cycle_start as t
import usage

import cycle_start

ROOT = Path(__file__).resolve().parent.parent
PREFIXES = {"agent/", "claude/", "ccr-"}


def test_the_workflows_name_the_same_prefixes():
    for name in ("automerge", "unconflict", "ci"):
        text = (ROOT / ".github/workflows" / f"{name}.yml").read_text()
        found = set(re.findall(r"startsWith\([^,]+, '([^']+)'\)", text))
        for group in re.findall(r'test\(\\"\^\(([^)]*)\)', text):
            found |= set(group.split("|"))
        assert found == PREFIXES, name


def test_the_tools_name_the_same_prefixes():
    assert set(cycle_start.AGENT) == PREFIXES
    for mod in (usage, operator_check):
        text = Path(mod.__file__).read_text()
        assert {p for g in re.findall(r"startswith\(\(([^)]*)\)\)", text) for p in re.findall(r'"([^"]+)"', g)} \
            == PREFIXES, mod.__name__


def test_a_red_owner_session_pr_is_work():
    pr = t.pr(ref="ccr-759dab36-7mz8bi")
    assert "take it over" in cycle_start.pr_work(pr, t.ISSUES, t.RED, None, t.NOW)
    assert cycle_start.pr_work(t.pr(["hold"], ref="ccr-1"), t.ISSUES, t.RED, None, t.NOW) is None
