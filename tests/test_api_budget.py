"""Fewer REST calls of the workflow token (2026-10-29: "API rate limit exceeded for installation" at 14:21 to 14:26):
`claim.py 0 --prune` deletes the claim refs with git and one API read, and the pacer records the REST budget."""
import os
import subprocess

import pytest

import claim
import pacer

NOW = 1_800_000_000
DAY = 86400


def test_prunable_takes_closed_tickets_closed_epics_and_old_locks():
    tips = {"7": NOW, "7-2": NOW, "8": NOW - 9 * DAY, "9-3": NOW,             # 8 is open: its old claim stays
            "comment-123": NOW - 2 * DAY, "comment-124": NOW - 3600, "review-200pr-3400-1": NOW - 2 * DAY,
            "roadmap-100pr-1-1": NOW - 3600, "fixmain-abc": NOW - 2 * DAY,
            "refill-0-202610290010": NOW - 2 * DAY, "refill-0-202610291400": NOW - 3600,
            "refill-50-3": NOW - 3600, "refill-51-4-2026102914x": NOW - 3600, "refill-52-1": NOW - 8 * DAY}
    gone = claim.prunable(tips, open_numbers={8, 51, 52}, now=NOW)
    assert gone == sorted(["7", "7-2", "9-3", "comment-123", "review-200pr-3400-1", "fixmain-abc",
                           "refill-50-3", "refill-52-1"])
    assert "refill-0-202610290010" not in gone                             # E = 0 keeps its locks for 7 days


@pytest.fixture
def clone(tmp_path, monkeypatch):
    """A bare remote with claim refs of several ages, and a clone of it as the working directory."""
    run = lambda *a, cwd=tmp_path, env=None: subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True,
                                                             env=env).stdout.strip()
    bare, work = tmp_path / "remote.git", tmp_path / "work"
    run("git", "init", "-q", "--bare", str(bare))
    run("git", "init", "-q", str(work))
    run("git", "remote", "add", "origin", str(bare), cwd=work)
    for name, age in (("7", 0), ("8", 0), ("comment-1", 2 * DAY), ("comment-2", 0), ("refill-0-x", 8 * DAY)):
        t = f"@{NOW - age} +0000"
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t", "GIT_AUTHOR_DATE": t, "GIT_COMMITTER_DATE": t}
        sha = run("git", "commit-tree", claim.EMPTY_TREE, "-m", f"Claim {name}", cwd=work, env=env)
        run("git", "push", "-q", "origin", f"{sha}:refs/heads/claim/{name}", cwd=work)
    monkeypatch.chdir(work)
    return bare


def names(bare):
    out = subprocess.run(["git", "for-each-ref", "refs/heads/claim", "--format=%(refname:lstrip=3)"], cwd=bare,
                         capture_output=True, text=True).stdout.split()
    return sorted(out)


def test_prune_deletes_with_git_and_keeps_the_open_and_new_ones(clone):
    gone = claim.prune(now=NOW, open_numbers={8, 1})
    assert sorted(gone) == ["7", "comment-1", "refill-0-x"]
    assert names(clone) == ["8", "comment-2"]
    assert claim.prune(now=NOW, open_numbers={8, 1}) == []                  # nothing left to delete


def test_prune_deletes_nothing_when_the_open_issues_cannot_be_read(clone, monkeypatch):
    import dashboard
    monkeypatch.setattr(dashboard, "pages", lambda path, limit=10: [])
    with pytest.raises(SystemExit) as e:
        claim.prune(now=NOW)
    assert e.value.code == 2 and len(names(clone)) == 5


def test_the_pacer_record_holds_the_rest_budget_and_no_token_gives_none():
    import datetime
    at = datetime.datetime(2026, 10, 29, 15, tzinfo=datetime.timezone.utc)
    gh = {"limit": 1000, "used": 412, "remaining": 588, "reset": NOW}
    assert pacer.record(at, {}, 0.01, None, 0, {}, {}, "x", github=gh)["github"] == gh
    assert pacer.github_limit(env={}) is None
