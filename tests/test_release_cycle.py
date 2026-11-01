"""The release cycle (owner, 2026-11-01): the scope of a release epic on the dashboard, and the `rank` tickets after a
release, which wait for a deep run (no candidate) and start one (a refill source)."""
import datetime

import dashboard
import usage

NOW = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
EPIC = dict(number=10, title="Release v0.1.0", labels=[{"name": "epic"}, {"name": dashboard.RELEASE}],
            body="Scope:\n- [x] #11\n- [ ] #12\n  - [ ] #13\nNot scope: #14\n")


def issue(n, *names):
    return dict(number=n, title=f"Ticket {n}", labels=[{"name": x} for x in names], body="")


def test_release_scope_lists_the_checklist():
    assert dashboard.release_scope(EPIC, [EPIC, issue(12), issue(14)]) == ([11, 12, 13], [12])


def test_the_dashboard_shows_the_scope_of_the_release_epic():
    issues = [EPIC, issue(12, "P1"), issue(13, "P2")]
    body = dashboard.render("", issues, {}, [], [], [], NOW, nxt=[], releases=dict(rows=[("Next", {}, 50, 2)]))
    assert "Release v0.1.0 (#10): 1 of 3 scope tickets closed, open: #12 #13" in body


def test_a_rank_ticket_waits_and_starts_a_refill_run():
    issues = [issue(1, "P3", dashboard.RANK), issue(2, "P3")]
    assert [i["number"] for i in dashboard.candidates(issues, now=NOW)] == [2]
    assert usage.refill_need(5, 1, issues) == "rank 1 tickets after the release"
    assert usage.refill_need(5, 1, [issue(2, "P3")]) == ""


def test_a_release_epic_with_open_scope_needs_no_epic_check():
    assert usage.refill_need(5, 1, [EPIC, issue(12, "P1")]) == ""
    assert usage.refill_need(5, 1, [EPIC]) == "epic check #10"
