"""A ticket with the label `after-release` waits for the next release (#4175): no candidate, no epic check, and the
dashboard counts it."""
import datetime

import dashboard
import usage


def issue(n, *names, body=""):
    return dict(number=n, title=f"Ticket {n}", labels=[{"name": x} for x in ("P2",) + names], body=body)


def test_held_ticket_is_no_candidate():
    issues = [issue(1), issue(2, dashboard.AFTER), issue(3, dashboard.AFTER, "P0")]
    assert [i["number"] for i in dashboard.candidates(issues)] == [1]


def test_ticket_that_depends_on_a_held_ticket_waits():
    issues = [issue(2, dashboard.AFTER), issue(4, body="Depends on: #2")]
    assert dashboard.candidates(issues) == []


def test_held_epic_needs_no_epic_check():
    assert usage.refill_need(0, 1, [issue(5, "epic", dashboard.AFTER)]) == ""
    assert usage.refill_need(0, 1, [issue(5, "epic")]) == "epic check #5"


def test_dashboard_counts_held_tickets():
    now = datetime.datetime(2026, 10, 29, 20, 0, tzinfo=datetime.timezone.utc)
    body = dashboard.render("", [issue(2, dashboard.AFTER), issue(3, dashboard.AFTER)], {}, [], [], [], now)
    assert "After the release: 2 tickets" in body.split("### Waiting for you")[1].split("###")[0]
