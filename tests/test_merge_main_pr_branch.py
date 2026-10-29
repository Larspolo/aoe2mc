"""merge_main.py --push N --pr-branch B: a run that took over a PR from its session branch guards and pushes B (#3678)."""
import subprocess
import types

import merge_main


def calls(monkeypatch, pr_branch):
    """The guard command and the git push arguments of push(5, pr_branch) on the local branch `session`."""
    seen = {"git": []}

    def run(cmd, **kw):
        seen["guard"] = cmd[1:]
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    def git(*args, check=False):
        seen["git"].append(args)
        return types.SimpleNamespace(returncode=0, stdout="session\n" if args[0] == "branch" else "", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(merge_main, "git", git)
    assert merge_main.push(5, pr_branch)
    return seen["guard"][1:], [a for a in seen["git"] if a[0] == "push"]


def test_a_takeover_guards_and_pushes_the_branch_of_the_pr(monkeypatch):
    guard, pushes = calls(monkeypatch, "claude/other-run")
    assert guard == ["5", "--guard", "--pr-branch", "claude/other-run"]
    assert pushes == [("push", "origin", "HEAD:refs/heads/claude/other-run")]


def test_without_it_the_current_branch_is_pushed(monkeypatch):
    guard, pushes = calls(monkeypatch, None)
    assert guard == ["5", "--guard"]
    assert pushes == [("push", "origin", "HEAD:refs/heads/session")]
