"""The release cycle (owner, 2026-11-01): the scope of a release epic is the GitHub milestone of its version; the
dashboard shows it, and the `rank` tickets after a release wait for a deep run (no candidate) and start one."""
import datetime

import dashboard
import usage

NOW = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
EPIC = dict(number=10, title="Release v0.1.0", labels=[{"name": "epic"}, {"name": dashboard.RELEASE}], body="")
MS = dict(title="v0.1.0", open_issues=2, closed_issues=3)


def issue(n, *names, milestone=None):
    return dict(number=n, title=f"Ticket {n}", labels=[{"name": x} for x in names], body="", milestone=milestone)


def test_release_scope_is_the_milestone_of_the_version():
    issues = [EPIC, issue(12, milestone=MS), issue(13, milestone=dict(MS, title="v0.2.0")), issue(14)]
    assert dashboard.release_version(EPIC) == "v0.1.0"
    assert dashboard.release_scope(EPIC, issues) == (3, 5, [12])                  # the counts of the issue's milestone
    assert dashboard.release_scope(EPIC, [EPIC], [MS]) == (3, 5, [])              # the counts of the milestone list
    assert dashboard.release_scope(EPIC, [EPIC]) == (0, 0, [])                    # no milestone yet
    assert dashboard.release_scope(dict(EPIC, title="Release"), issues) == (0, 0, [])


def test_the_dashboard_shows_the_milestone_of_the_release_epic():
    issues = [EPIC, issue(12, "P1", milestone=MS), issue(13, "P2", milestone=MS)]
    body = dashboard.render("", issues, {}, [], [], [], NOW, nxt=[], releases=dict(rows=[("Next", {}, 50, 2)]))
    assert "Release v0.1.0 (#10): 3 of 5 tickets of the milestone `v0.1.0` closed, open: #12 #13" in body


def test_a_rank_ticket_waits_and_starts_a_refill_run():
    issues = [issue(1, "P3", dashboard.RANK), issue(2, "P3")]
    assert [i["number"] for i in dashboard.candidates(issues, now=NOW)] == [2]
    assert usage.refill_need(5, 1, issues) == "rank 1 tickets after the release"
    assert usage.refill_need(5, 1, [issue(2, "P3")]) == ""


def test_a_release_epic_with_open_milestone_tickets_needs_no_epic_check():
    assert usage.refill_need(5, 1, [EPIC, issue(12, "P1", milestone=MS)]) == ""
    assert usage.refill_need(5, 1, [EPIC]) == "epic check #10"
