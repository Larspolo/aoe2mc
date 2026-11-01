"""The release tags a green head of main, also when it is from before the close of the epic (#5577)."""
import os
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSED = "2026-11-01T14:36:00Z"

FAKE = """#!/bin/bash
echo "$*" >> "$LOG"
case "$*" in
  *"issues?state=closed"*) echo 7 ;;
  *"issues/7 --jq .title"*) echo "Release v0.1.0" ;;
  *"issues/7 --jq .closed_at"*) echo "$CLOSED" ;;
  *"git/ref/tags/"*) exit 1 ;;
  *"milestones?state=all"*) echo "3 0" ;;
  *"ci.yml/runs"*) echo "$GREEN" ;;
  *"commits/main"*) echo "$HEAD" ;;
  "issue create"*) echo "https://example/issues/8" ;;
esac
"""


def step():
    jobs = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())["jobs"]
    return next(s["run"] for s in jobs["release"]["steps"] if s["name"] == "Tag the closed release epics")


def run(tmp_path, green, head):
    (tmp_path / "gh").write_text(FAKE)
    (tmp_path / "gh").chmod(0o755)
    log = tmp_path / "log"
    log.write_text("")
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", LOG=str(log), CLOSED=CLOSED,
               GREEN=green, HEAD=head, R="o/r", BRANCH="main")
    out = subprocess.run(["bash", "-e", "-c", step()], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout, log.read_text()


def test_green_head_from_before_the_close_is_tagged(tmp_path):
    out, log = run(tmp_path, "aaa 2026-11-01T14:00:00Z", "aaa")
    assert "released #7 as v0.1.0" in out
    assert "ref=refs/tags/v0.1.0 -f sha=aaa" in log


def test_old_green_commit_that_is_not_the_head_waits(tmp_path):
    out, log = run(tmp_path, "aaa 2026-11-01T14:00:00Z", "bbb")
    assert "wait #7 (v0.1.0): no green CI run of a commit after the close" in out
    assert "refs/tags" not in log.replace("git/ref/tags", "")


def test_green_commit_after_the_close_is_tagged(tmp_path):
    out, log = run(tmp_path, "aaa 2026-11-01T15:00:00Z", "bbb")
    assert "sha=aaa" in log
