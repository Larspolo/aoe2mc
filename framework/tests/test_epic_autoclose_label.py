"""`epic_autoclose.merged_pr` also accepts a close by the label `close` (#6065): a check ticket with no bug closes with
the label and no PR (#6053), and its epic must close by itself as after a merge."""
import dashboard
import epic_autoclose
import pytest

ISSUE = {"state": "closed", "state_reason": "completed"}
RUN = {"login": "Larspolo"}                         # the runs post as the owner
BOT = {"login": "github-actions[bot]"}


def labeled(actor=RUN, name="close", at="2026-11-07T15:09:50Z"):
    return {"event": "labeled", "label": {"name": name}, "actor": actor, "created_at": at}


def closed(at="2026-11-07T15:10:03Z"):
    return {"event": "closed", "commit_id": None, "actor": BOT, "created_at": at}


@pytest.fixture
def github(monkeypatch):
    def setup(events, issue=ISSUE):
        monkeypatch.setattr(dashboard, "pages", lambda path: events)
        monkeypatch.setattr(dashboard, "api", lambda path, *a: issue if path.startswith("issues/") else [])
    return setup


def test_a_close_by_the_label_of_a_run_counts(github):
    github([labeled(), closed()])
    assert epic_autoclose.merged_pr(6053) == epic_autoclose.LABEL


def test_a_close_by_hand_with_no_label_gives_none(github):
    github([labeled(name="check"), closed()])
    assert epic_autoclose.merged_pr(6053) is None


def test_the_label_of_another_user_does_not_count(github):
    github([labeled(actor={"login": "stranger"}), closed()])
    assert epic_autoclose.merged_pr(6053) is None


def test_a_label_after_the_close_does_not_count(github):
    github([closed(), labeled(at="2026-11-07T15:20:00Z")])
    assert epic_autoclose.merged_pr(6053) is None


def test_a_ticket_closed_as_not_planned_gives_none(github):
    github([labeled(), closed()], issue={"state": "closed", "state_reason": "not_planned"})
    assert epic_autoclose.merged_pr(6053) is None


def test_the_evidence_names_the_label_in_place_of_a_pr():
    text = epic_autoclose.evidence(6053, epic_autoclose.LABEL, {"html_url": "https://x/c/1"})
    assert "#6053" in text and "`close`" in text and "PR #" not in text
    assert "PR #6055" in epic_autoclose.evidence(6052, 6055, {"html_url": "https://x/c/1"})
