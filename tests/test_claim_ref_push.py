"""A run never pushes its work to a claim ref: PR #5972 came from `claim/5942-2`, so Automerge did not merge it, and
`claim.py --release` read the work commit as the claim of another run (#5942)."""
import json
import os
import subprocess
import types

import merge_main
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "guard-shell.sh")


def pushes(monkeypatch, branch, pr_branch=None):
    seen = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: types.SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(merge_main, "git", lambda *a, check=False: seen.append(a) or types.SimpleNamespace(
        returncode=0, stdout=branch + "\n" if a[0] == "branch" else "", stderr=""))
    return merge_main.push(5, pr_branch), [a for a in seen if a[0] == "push"]


@pytest.mark.parametrize("branch, pr_branch", [("claim/5", None), ("claim/5-2", None), ("claude/x", "claim/5-2")])
def test_push_refuses_a_claim_ref(monkeypatch, capsys, branch, pr_branch):
    assert pushes(monkeypatch, branch, pr_branch) == (False, [])
    assert "claim ref" in capsys.readouterr().out


def test_push_takes_a_session_branch(monkeypatch):
    assert pushes(monkeypatch, "claude/x") == (True, [("push", "origin", "HEAD:refs/heads/claude/x")])


def hook(command):
    return subprocess.run([HOOK], input=json.dumps({"tool_input": {"command": command}, "cwd": ROOT}),
                          capture_output=True, text=True).returncode


@pytest.mark.parametrize("command", [
    "git push origin HEAD:claim/5942-2",
    "git push -u origin HEAD:refs/heads/claim/5942",
    "git checkout -B claim/5942-2 origin/claim/5942-2",
    "git checkout -b claude/x origin/claim/5942-2",
    "git switch claim/5942",
])
def test_hook_blocks_a_claim_ref(command):
    assert hook(command) == 2, command


@pytest.mark.parametrize("command", [
    "git push -u origin claude/dreamy-turing-abeym5",
    "git checkout -B claude/x origin/claude/y",
    "git ls-remote origin 'refs/heads/claim/*'",
    "python3 framework/tools/claim.py 5942 --release",
])
def test_hook_lets_other_commands_pass(command):
    assert hook(command) == 0, command
