"""tools/claim.py: the guard reads the own commits of a shallow clone only after a full fetch (#4471): else the merged
commits of main below the shallow end look like own commits that close other tickets."""
import subprocess

import claim


def test_a_shallow_clone_is_fetched_in_full_before_the_scan(monkeypatch):
    calls = []

    def git(*args, check=True):
        calls.append(args)
        out = "true\n" if args[0] == "rev-parse" else ""
        return subprocess.CompletedProcess(args, 0, out, "")

    monkeypatch.setattr(claim, "git", git)
    assert claim.foreign(7, "origin/main") == []
    assert calls[1] == ("fetch", "-q", "--unshallow", "origin") and calls[2][0] == "log"


def test_a_full_clone_is_not_fetched(monkeypatch):
    calls = []

    def git(*args, check=True):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "false\n" if args[0] == "rev-parse" else "", "")

    monkeypatch.setattr(claim, "git", git)
    claim.foreign(7, "origin/main")
    assert [c[0] for c in calls] == ["rev-parse", "log"]
