"""tools/cycle_start.py prints only the open agent PRs that need work (owner, 2026-10-28)."""
import datetime

import cycle_start as start

NOW = datetime.datetime(2026, 10, 28, 12, 0, tzinfo=datetime.timezone.utc)


def pr(labels=(), body="Closes #7", ref="claude/x-1", minutes=20):
    created = (NOW - datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"number": 70, "head": {"ref": ref}, "body": body, "created_at": created,
            "labels": [{"name": n} for n in labels]}


ISSUES = {7: {"number": 7, "labels": [{"name": "in-progress"}]}, 8: {"number": 8, "labels": [{"name": "needs-human"}]}}
RED, GREEN = [("quick", "completed", "failure")], [("quick", "completed", "success")]


def test_a_red_pr_is_work_unless_its_run_is_alive():
    assert "take it over" in start.pr_work(pr(), ISSUES, RED, (31, "Beat #7 by claude/x-1"), NOW)
    assert "leave it" in start.pr_work(pr(), ISSUES, RED, (5, "Beat #7 by claude/x-1"), NOW)
    assert "take it over" in start.pr_work(pr(["conflict"]), ISSUES, [], (12, "Beat #7 by claude/x-1"), NOW)


def test_waiting_running_and_young_prs_need_no_work():
    assert start.pr_work(pr(body="Closes #8"), ISSUES, RED, None, NOW) is None               # needs-human ticket
    assert start.pr_work(pr(), ISSUES, [("quick", "in_progress", None)], None, NOW) is None
    assert start.pr_work(pr(minutes=5), ISSUES, GREEN, None, NOW) is None
    assert start.pr_work(pr(ref="feature/x"), ISSUES, RED, None, NOW) is None                 # not an agent PR
    assert "Automerge sweep" in start.pr_work(pr(), ISSUES, GREEN, None, NOW)
    assert "ticket is closed" in start.pr_work(pr(body="Closes #9"), ISSUES, GREEN, None, NOW)


def test_beats_take_the_top_slot():
    t = int(NOW.timestamp())
    got = start.beats([f"7 {t - 3600} Claim #7 by a", f"7-2 {t - 120} Beat #7 by b", "x y"], NOW)
    assert got == {7: (2.0, "Beat #7 by b")}


def test_the_prs_of_this_run_are_its_own():
    beat, run = (5, "Beat #7 by claude/kind-a1b2c3"), "claude/kind-a1b2c3"          # a session branch ends in letters
    assert "a PR of this run" in start.pr_work(pr(ref=run), ISSUES, RED, beat, NOW, me=run + "-2")
    assert "a PR of this run" in start.pr_work(pr(ref=run + "-3"), ISSUES, RED, beat, NOW, me=run)
    assert "leave it" in start.pr_work(pr(ref="claude/kind-a1b2c4"), ISSUES, RED, beat, NOW, me=run)
