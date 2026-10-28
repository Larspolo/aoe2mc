"""The pacer starts the extra refill runs only while the refills still make tickets (2026-10-28)."""
import datetime

import usage

NOW = datetime.datetime(2026, 10, 28, 7, 0, tzinfo=datetime.timezone.utc).timestamp()


def issue(minutes_ago, pr=False):
    t = datetime.datetime.fromtimestamp(NOW - minutes_ago * 60, datetime.timezone.utc)
    return {"created_at": t.strftime("%Y-%m-%dT%H:%M:%SZ"), **({"pull_request": {}} if pr else {})}


def test_new_tickets_keep_the_refill_runs():
    assert usage.refill_runs([issue(300), issue(20)], NOW, refill=3) == 3


def test_no_new_ticket_gives_one_refill_run():
    assert usage.refill_runs([issue(300), issue(61)], NOW, refill=3) == 1
    assert usage.refill_runs([issue(300), issue(5, pr=True)], NOW, refill=3) == 1   # a new PR is no new ticket
    assert usage.refill_runs([], NOW, refill=0) == 0


def test_the_guard_changes_the_plan():
    old = [issue(300)]
    assert usage.lane_plan(40, 17, 3, 0, 0.25, False, hi=8, refill=usage.refill_runs(old, NOW, refill=3)) == (4, 0)
    new = old + [issue(10)]
    assert usage.lane_plan(40, 17, 3, 0, 0.25, False, hi=8, refill=usage.refill_runs(new, NOW, refill=3)) == (6, 0)
