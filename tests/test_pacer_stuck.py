"""The pacer takes over each stuck ticket for one run (#4356): runs with no brief raced for the same stuck PRs, and
each lost race cost a cycle start."""
import os
import subprocess
import time

import pytest

import claim
import dashboard
import pacer
import ticket_context

OLD = int(time.time()) - 2 * claim.STALE          # a claim with no beat for an hour: its run stopped


def git(*args, cwd, env=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
                          env={**os.environ, **(env or {})}).stdout.strip()


@pytest.fixture
def clone(tmp_path, monkeypatch):
    """A clone (the pacer) of a bare remote that holds the stale claim of ticket 4 of the stopped run `run-old`."""
    remote, d = tmp_path / "remote.git", tmp_path / "pacer"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "run-0", str(d), cwd=tmp_path)
    git("remote", "add", "origin", str(remote), cwd=d)
    for k, v in (("user.name", "t"), ("user.email", "t@t")):
        git("config", k, v, cwd=d)
    sha = git("commit-tree", claim.EMPTY_TREE, "-m", "Claim #4 by run-old (abc)", cwd=d,
              env={"GIT_COMMITTER_DATE": f"{OLD} +0000"})
    git("push", "-q", "origin", f"{sha}:refs/heads/claim/4", cwd=d)
    monkeypatch.chdir(d)
    return d


def issue(n, labels=(), updated=OLD):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(updated))
    return {"number": n, "title": f"T{n}", "body": "b", "labels": [{"name": x} for x in labels], "updated_at": stamp}


PR = {"number": 40, "body": "Closes #4", "head": {"ref": "claude/old"}}
REFS = [f"4 {OLD} Claim #4 by run-old (abc)"]


def briefs(monkeypatch, open_all, ready):
    monkeypatch.setattr(pacer, "red_main", lambda: False)
    monkeypatch.setattr(pacer, "queues", lambda open_all, refs, now, tasks: {t: list(ready) for t in tasks})
    monkeypatch.setattr(ticket_context, "context", lambda body: "")
    monkeypatch.setattr(dashboard, "pages", lambda path, limit=10: [PR] if path.startswith("pulls") else [])
    found = {"five_hour": (0.2, 0, "allowed")}
    return pacer.Briefs([("main", "u", "t")], {"open": open_all, "refs": REFS}, time.time(), found)


def test_two_runs_get_the_takeover_and_the_next_candidate(clone, monkeypatch):
    started = []
    monkeypatch.setattr(claim, "start", lambda n, by=None, note="", word="Started by": started.append((n, word)))
    monkeypatch.setattr(pacer, "send", lambda url, token, text=None: {})
    b = briefs(monkeypatch, [issue(4, ["in-progress"]), issue(5)], [issue(5)])
    texts = [b.take("main"), b.take("main")]
    head = [dict(x.split(": ", 1) for x in t[2].split("\n\n")[0].split("\n")[1:]) for t in texts]
    assert [h["ticket"] for h in head] == ["4", "5"]
    assert head[0]["takeover"] == "PR #40 claude/old" and "takeover" not in head[1]
    assert claim.subject("claim/4-2").startswith(f"Claim #4 by {head[0]['claim']} ")    # the next slot of the ticket
    assert claim.claim(4, takeover=True, by="run-late") is None     # a run with no brief cannot take it now
    b.start("main", "u", "t")                                        # nothing left: a run with no brief
    assert b.take("main") is None


def test_the_comment_of_a_takeover(clone, monkeypatch):
    started = []
    monkeypatch.setattr(claim, "start", lambda n, by=None, note="", word="Started by": started.append((n, word)))
    monkeypatch.setattr(pacer, "send", lambda url, token, text=None: {})
    b = briefs(monkeypatch, [issue(4, ["in-progress"]), issue(5)], [issue(5)])
    b.start("main", "u", "t")
    b.start("main", "u", "t")
    assert started == [(4, "Taken over by"), (5, "Started by")] and b.given == [4, 5]


def test_a_live_claim_and_a_reserved_lane_are_no_takeover_of_main(monkeypatch):
    monkeypatch.setattr(dashboard, "RESERVED", ("deep",))
    now = time.time()
    open_all = [issue(4, ["in-progress"]), issue(6, ["in-progress", "lane:deep"]), issue(7, ["in-progress"], now)]
    refs = REFS + [f"6 {OLD} Release #6 by run-old", f"7 {int(now)} Beat #7 by run-live"]
    got = pacer.stuck(open_all, refs, now, [PR])
    assert [(i["number"], t) for i, t in got] == [(4, "PR #40 claude/old"), (6, "no PR")]
    assert [pacer.fits(i, "main") for i, _ in got] == [True, False] and pacer.fits(got[1][0], "deep")
    assert pacer.stuck(open_all, None, now, [PR]) == []             # no claim refs: no ticket looks stuck
