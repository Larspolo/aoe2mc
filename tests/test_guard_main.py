"""The PreToolUse hook blocks a force push, a history rewrite or a delete of main, and nothing else."""
import json
import os
import subprocess

import pytest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "hooks", "guard-main.sh")


def run(command):
    return subprocess.run([HOOK], input=json.dumps({"tool_input": {"command": command}}), capture_output=True,
                          text=True).returncode


@pytest.mark.parametrize("command", [
    "git push --force-with-lease origin main",
    "git push origin +main",
    "git push origin +HEAD:main",
    "git push -f origin HEAD:refs/heads/main",
    "git push origin :main",
    "git push origin --delete main",
    "git push --mirror origin",
    "cd /repo && git push --force-with-lease=main:abc origin main 2>&1 | tail -2",
    "git -C /repo push --force origin main",
    "gh api -X PATCH repos/Larspolo/aoe2mc/git/refs/heads/main -F force=true -f sha=abc",
    "gh api repos/Larspolo/aoe2mc/git/refs/heads/main -X DELETE",
])
def test_blocks(command):
    assert run(command) == 2, command


@pytest.mark.parametrize("command", [
    "git push -u origin claude/gallant-volta-7pq7j6",
    "git push --force-with-lease origin claude/fix-main-sidebar",
    "git push --porcelain origin abc123:refs/heads/claim/12",
    "git push origin main",
    "git fetch origin main && git merge origin/main",
    "gh api repos/Larspolo/aoe2mc/git/refs/heads/main",
    "git commit -F - <<'EOF'\nDo not run git push --force origin main\nEOF",
    "echo 'git push --force origin main' > notes.txt",
    "python3 -m pytest -q",
])
def test_allows(command):
    assert run(command) == 0, command
