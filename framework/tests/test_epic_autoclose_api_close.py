"""`epic_autoclose.merged_pr` finds the PR also when automerge.yml closed the ticket by the API (#6061): that close
event has no commit, so the PR comes from the "referenced" event of its merge commit."""
import dashboard
import epic_autoclose
import pytest

ISSUE = {"state": "closed", "state_reason": "completed"}
MERGE = {"event": "referenced", "commit_id": "e69fa82", "created_at": "2026-11-07T14:51:44Z"}
BRANCH = {"event": "referenced", "commit_id": "0a598ac", "created_at": "2026-11-07T14:46:30Z"}


@pytest.fixture
def github(monkeypatch):
    """events: the events of #6052; pulls: {sha: [PR]}."""
    def setup(events, pulls, issue=ISSUE):
        monkeypatch.setattr(dashboard, "pages", lambda path: events)
        monkeypatch.setattr(dashboard, "api", lambda path, *a: issue if path.startswith("issues/") else
                            pulls.get(path.split("/")[1], []))
    return setup


def closed(commit=None, at="2026-11-07T14:51:46Z"):
    return {"event": "closed", "commit_id": commit, "created_at": at}


PR = {"number": 6055, "merged_at": "2026-11-07T14:51:42Z"}


def test_a_close_by_the_api_takes_the_pr_of_the_merge_commit(github):
    github([BRANCH, MERGE, closed()], {"e69fa82": [PR], "0a598ac": [PR]})
    assert epic_autoclose.merged_pr(6052) == 6055


def test_a_close_by_the_closing_word_takes_the_pr_of_its_commit(github):
    github([MERGE, closed("e69fa82")], {"e69fa82": [PR]})
    assert epic_autoclose.merged_pr(6052) == 6055


def test_a_close_by_hand_with_no_merged_pr_gives_none(github):
    github([closed()], {})
    assert epic_autoclose.merged_pr(6052) is None


def test_a_pr_that_merged_long_before_the_close_does_not_count(github):
    old = {"number": 6000, "merged_at": "2026-11-07T10:00:00Z"}   # a PR that only named the ticket
    github([MERGE, closed()], {"e69fa82": [old]})
    assert epic_autoclose.merged_pr(6052) is None


def test_an_open_pr_of_a_referenced_commit_does_not_count(github):
    github([BRANCH, closed()], {"0a598ac": [{"number": 6055, "merged_at": None}]})
    assert epic_autoclose.merged_pr(6052) is None


def test_a_ticket_closed_as_not_planned_gives_none(github):
    github([MERGE, closed()], {"e69fa82": [PR]}, issue={"state": "closed", "state_reason": "not_planned"})
    assert epic_autoclose.merged_pr(6052) is None
