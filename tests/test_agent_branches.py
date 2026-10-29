"""Each place that names the branches of agent PRs names the same prefixes as cycle_start.AGENT (#3382)."""
import re
from pathlib import Path

import operator_check
import test_cycle_start as t
import unconflict_pick
import usage

import cycle_start

ROOT = Path(__file__).resolve().parent.parent


def test_the_workflows_name_the_same_prefixes():
    for name in ("automerge", "ci"):
        text = (ROOT / ".github/workflows" / f"{name}.yml").read_text()
        found = set(re.findall(r"startsWith\([^,]+, '([^']+)'\)", text))
        for group in re.findall(r'test\(\\?"\^\(([^)]*)\)', text):  # automerge.yml: unescaped in AGENT (#3383)
            found |= set(group.split("|"))
        assert found == set(cycle_start.AGENT), name
    assert unconflict_pick.AGENT is cycle_start.AGENT       # unconflict.yml picks its PRs with this tool (2026-10-29)


def test_the_tools_name_the_same_prefixes():
    for mod in (usage, operator_check):
        text = Path(mod.__file__).read_text()
        assert {p for g in re.findall(r"startswith\(\(([^)]*)\)\)", text) for p in re.findall(r'"([^"]+)"', g)} \
            == set(cycle_start.AGENT), mod.__name__


def test_a_red_owner_session_pr_is_work():
    pr = t.pr(ref="ccr-759dab36-7mz8bi")
    assert "take it over" in cycle_start.pr_work(pr, t.ISSUES, t.RED, None, t.NOW)
    assert cycle_start.pr_work(t.pr(["hold"], ref="ccr-1"), t.ISSUES, t.RED, None, t.NOW) is None
