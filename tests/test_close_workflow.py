"""close.yml closes the issue of its own `labeled` event, also when the list API does not return it yet (#5575)."""
import os
import shutil
import subprocess

import pytest
import yaml

WORKFLOW = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", "close.yml")

# A fake `gh`: FAKE_LIST is the output of the label list, FAKE_<N> the `state labels` line of issue N.
FAKE_GH = r"""#!/usr/bin/env bash
echo "$*" >> "$LOG"
case "$*" in
  *"labels=close"*) for i in $FAKE_LIST; do echo "$i"; done ;;
  *"/pulls?"*) echo "[]" ;;
  "api repos/$R/issues/"*" --jq "*) v="FAKE_${2##*/}"; echo "${!v}" ;;
esac
"""


def script():
    steps = yaml.safe_load(open(WORKFLOW))["jobs"]["close"]["steps"]
    return next(s["run"] for s in steps if s["name"] == "Close the issues with the label close")


def run(tmp_path, event, listed, issues):
    gh = tmp_path / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    log = tmp_path / "log"
    log.write_text("")
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", LOG=str(log), R="o/r", EV=event,
               FAKE_LIST=" ".join(map(str, listed)), **{f"FAKE_{n}": v for n, v in issues.items()})
    subprocess.run(["bash", "-e", "-c", script()], env=env, check=True, capture_output=True, timeout=30)
    return log.read_text().splitlines()


def closed(calls):
    return [c.split()[1].rsplit("/", 1)[1] for c in calls if "state=closed" in c and "/issues/" in c]


pytestmark = pytest.mark.skipif(not shutil.which("jq"), reason="close.yml pipes the PR list to jq")


def test_event_issue_closes_when_the_list_lags(tmp_path):
    calls = run(tmp_path, "7", [], {7: "open P1 epic close release"})
    assert closed(calls) == ["7"]
    assert any(c.startswith("workflow run release.yml") for c in calls)


def test_event_issue_in_the_list_closes_once(tmp_path):
    calls = run(tmp_path, "7", [7, 8], {7: "open close P2", 8: "open P2 close"})
    assert closed(calls) == ["7", "8"]
    assert sum("comments" in c for c in calls) == 2


def test_closed_or_unlabeled_event_issue_is_skipped(tmp_path):
    assert closed(run(tmp_path, "7", [], {7: "closed P2"})) == []
    assert closed(run(tmp_path, "7", [], {7: "open P2"})) == []


def test_cron_has_no_event_issue(tmp_path):
    assert closed(run(tmp_path, "", [9], {9: "open close"})) == ["9"]


def test_status_issue_stays_open(tmp_path):
    assert closed(run(tmp_path, "1", [], {1: "open agent-status close"})) == []
