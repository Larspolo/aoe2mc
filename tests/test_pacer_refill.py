"""The pacer starts the refill runs only when they have work (#3547): the queue is below the target, an epic waits for
its check, or a release check has no ticket. 5 deep runs in one hour found none of these (2026-10-29)."""
import usage


def issue(n, *names, body="", subs=None):
    i = dict(number=n, labels=[{"name": x} for x in names], body=body)
    if subs:
        i["sub_issues_summary"] = dict(total=subs[0], completed=subs[1])
    return i


def test_no_refill_runs_when_the_queue_holds_the_target_and_no_epic_waits():
    issues = [issue(1, "epic", subs=(5, 4)), issue(2, "epic", subs=(100, 100)), issue(3, "P3", body="Part of #2."),
              issue(4, "epic", "muted"), issue(5, "epic", "needs-human"), issue(6, "epic", "close")]
    assert usage.refill_need(42, 40, issues) == ""
    assert usage.refill_need(40, 40, issues, lambda: []) == ""
    lanes = [("haiku", 0, 0.25), ("deep", 0, 2.9)]
    assert usage.plan(40, 0, 42, lanes, False, refill=0, refill_lane="deep")[1]["deep"] == 0


def test_refill_runs_when_the_queue_is_below_the_target():
    assert usage.refill_need(3, 40, [], free=lambda: ["1 fallbacks"]) == "ready 3 < target 40: 1 fallbacks"


def test_refill_runs_for_an_epic_check_or_a_release_check():
    pr = dict(issue(3, body="Part of #2."), pull_request={})               # a PR is no open work of the epic
    assert usage.refill_need(42, 40, [issue(2, "epic", subs=(6, 6)), pr]) == "epic check #2"
    assert usage.refill_need(42, 40, [issue(7, "epic")]) == "epic check #7"                  # no sub-issue at all
    assert usage.refill_need(42, 40, [], lambda: [("C", 2, "play:check")]) == "1 release checks"
