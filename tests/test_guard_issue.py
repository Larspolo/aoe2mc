"""The hooks refuse an issue or comment body that is a file path, and a new issue with no spec (#4555)."""
import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, ".claude", "hooks")
SPEC = "## Goal\nFix it.\n\n## Acceptance criteria\n- [ ] It works.\n"


def run(hook, data):
    return subprocess.run([os.path.join(HOOKS, hook)], input=json.dumps(data), capture_output=True, text=True)


@pytest.mark.parametrize("tool, args, code", [
    ("mcp__github__issue_write", {"method": "create", "body": "@/tmp/x/t.md"}, 2),
    ("mcp__github__add_issue_comment", {"body": "See /tmp/claude-0/s/t.md"}, 2),
    ("mcp__github__issue_write", {"method": "create", "body": "Fix the bug."}, 2),
    ("mcp__github__issue_write", {"method": "create", "body": "## Goal\nFix it."}, 2),
    ("mcp__github__issue_write", {"method": "create", "body": SPEC}, 0),
    ("mcp__github__issue_write", {"method": "update", "body": "Fix the bug."}, 0),
    ("mcp__github__add_issue_comment", {"body": "Done in #12."}, 0),
])
def test_mcp_body(tool, args, code):
    r = run("guard-body.sh", {"tool_name": tool, "tool_input": args})
    assert r.returncode == code, args
    if code:
        assert "Blocked" in r.stderr


@pytest.mark.parametrize("command, code", [
    ("gh issue create --title x --body @/tmp/t.md", 2),
    ("gh issue comment 5 -b @t.md", 2),
    ("gh issue create --title x --body=@t.md", 2),
    ("gh api repos/a/b/issues -f body=@t.md", 2),
    ("gh issue create --title x --body-file t.md", 0),
    ("gh issue comment 5 --body 'Done in #12.'", 0),
])
def test_shell_body(command, code):
    assert run("guard-shell.sh", {"tool_input": {"command": command}, "cwd": ROOT}).returncode == code, command
