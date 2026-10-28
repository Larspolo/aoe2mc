"""Automerge merges a PR on any branch with the label `automerge`; `hold` wins over it (#3383)."""
import json
import os
import re
import subprocess

WORKFLOW = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "automerge.yml")


def agent_filter():
    return re.search(r"^\s*AGENT='(.*)'$", open(WORKFLOW).read(), re.M).group(1)


def pr(branch, *labels):
    return {"head": {"ref": branch, "repo": {"full_name": "o/r"}}, "labels": [{"name": n} for n in labels]}


def selected(prs):
    """The branches that the sweep filter (and merge()) takes, before the check of `hold`."""
    out = subprocess.run(["jq", "-r", f".[] | select({agent_filter()}) | .head.ref"], input=json.dumps(prs),
                         capture_output=True, text=True, check=True).stdout
    return out.split()


def test_label_takes_any_branch():
    prs = [pr("claude/x"), pr("ccr-y"), pr("owner/z", "automerge"), pr("owner/w"), pr("tool/v", "P2")]
    assert selected(prs) == ["claude/x", "ccr-y", "owner/z"]


def test_hold_wins_in_merge():
    text = open(WORKFLOW).read()
    assert text.index('select(.name == "hold")') < text.index('jq -e "$AGENT"')
    assert "select($AGENT)" in text


def test_label_listed():
    assert any(line.startswith("automerge|") for line in open(os.path.join(os.path.dirname(WORKFLOW), "..", "labels.txt")))
