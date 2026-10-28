"""The roadmap review counts the merged PRs from the later of `last_roadmap` and its newest lock ref (#3352): a write of
the status issue body can be lost, a lock ref cannot."""
import pytest

from test_claim import clones  # noqa: F401

import claim

STATE = "2026-10-28T06:47:32Z"
LOCK = "2026-10-28T09:15:30Z"
BODY = f'<!-- agent-state: {{"last_review": "{STATE}", "last_roadmap": "{STATE}", "review_prs": 50}} -->\n'


@pytest.fixture
def github(monkeypatch):
    """claim.main() on GitHub with stubs: the status body, the lock time, the merged PRs and the lock push."""
    seen = {"since": [], "keys": []}
    monkeypatch.setattr(claim, "deep_lane", lambda: True)
    monkeypatch.setattr(claim, "on_github", lambda remote="origin": True)
    monkeypatch.setattr(claim, "api", lambda path: {"body": BODY})
    monkeypatch.setattr(claim, "last_lock", lambda kind, remote="origin": seen.get("lock"))
    monkeypatch.setattr(claim, "merged_since", lambda last, gap, remote="origin": seen["since"].append(last) or seen["merged"])
    monkeypatch.setattr(claim, "claim_lock", lambda kind, key, remote="origin": seen["keys"].append(key) and False)
    return seen


def test_the_roadmap_counts_from_a_newer_lock(github):
    github.update(lock=LOCK, merged=99)
    assert claim.main(["0", "--roadmap"]) == 1
    assert github["since"] == [LOCK] and github["keys"] == []
    github["merged"] = 100
    claim.main(["0", "--roadmap"])
    assert github["keys"] == ["100pr-20261028T091530Z-1"]


def test_the_state_time_without_a_newer_lock(github):
    for lock in (None, "2026-10-28T04:08:11Z"):                                 # no lock ref, an older lock
        github.update(lock=lock, merged=100, since=[], keys=[])
        claim.main(["0", "--roadmap"])
        assert github["since"] == [STATE] and github["keys"] == ["100pr-20261028T064732Z-1"]


def test_the_process_review_keeps_the_state_time(github):
    github.update(lock=LOCK, merged=50)
    claim.main(["0", "--review"])
    assert github["since"] == [STATE] and github["keys"] == ["50pr-20261028T064732Z-1"]


def test_the_newest_lock_ref_gives_its_claim_time(clones, monkeypatch):  # noqa: F811
    monkeypatch.chdir(clones[0])
    assert claim.last_lock("roadmap") is None
    for key, at in (("249047", "2026-10-28T20:00:00Z"),                       # an old key form: not a gap lock
                    ("100pr-none-1", "2026-10-28T01:00:00Z"),
                    ("100pr-20261028T064732Z-2", LOCK),
                    ("100pr-20261028T064732Z-1", "2026-10-28T06:47:30Z"),
                    ("100pr-20261028T040813Z-1", "2026-10-28T04:08:11Z")):
        monkeypatch.setenv("GIT_COMMITTER_DATE", at)
        assert claim.claim_lock("roadmap", key)
    assert claim.last_lock("roadmap") == LOCK
    assert claim.last_lock("review") is None
