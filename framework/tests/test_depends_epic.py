"""A "Depends on" line that names a parent epic does not hold the ticket, and orphans start a refill run (#6049)."""
import datetime

import dashboard
import usage

NOW = datetime.datetime(2026, 11, 7, 12, 0, tzinfo=datetime.timezone.utc)
URL = "https://api.github.com/repos/o/r/issues/"


def issue(n, body="", labels=("P3",), parent=None):
    out = {"number": n, "title": f"Ticket {n}", "labels": [{"name": x} for x in labels], "body": body}
    if parent:
        out["parent_issue_url"] = URL + str(parent)
    return out


def ready(issues):
    return [i["number"] for i in dashboard.candidates(issues, now=NOW, reserved=())]


def test_a_ticket_that_names_its_own_epic_is_ready():
    issues = [issue(1, labels=("P3", "epic"), parent=None), issue(2, labels=("P3", "epic"), parent=1),
              issue(3, "Depends on: #2", parent=2), issue(4, "Depends on: #1", parent=2)]   # the epic and its parent
    assert {3, 4} <= set(ready(issues))


def test_another_open_ticket_still_holds_it():
    issues = [issue(1, labels=("P3", "epic")), issue(2, "Depends on: #1, #3", parent=1), issue(3, parent=1)]
    assert 2 not in ready(issues) and 3 in ready(issues)


def test_a_loop_of_parents_ends():
    a, b = issue(1, parent=2), issue(2, parent=1)
    assert dashboard.ancestors(a, {1: a, 2: b}) == [2, 1]


def test_blocked_on_its_own_epic_is_an_orphan():
    issues = [issue(1, labels=("P3", "epic")), issue(2, "Depends on: #1", labels=("P3", "blocked"), parent=1)]
    assert [n for n, _ in dashboard.orphans(issues)] == [2]


def test_orphans_are_a_refill_source():
    lost = [(7, "a \"Depends on\" cycle: remove the wrong line")]
    assert "#7" in usage.refill_need(0, 4, [], orphans=lambda: lost, now=NOW.timestamp())
    assert usage.refill_need(0, 4, [], orphans=lambda: [], now=NOW.timestamp()) == ""
