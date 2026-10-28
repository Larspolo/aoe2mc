"""The pacer starts `refill_runs` runs beyond the ready tickets, so that several epics refill at once (2026-10-28)."""
import usage


def test_refill_runs_come_on_top_of_the_ready_tickets():
    # 2026-10-28 05:45 UTC: target 40, 17 claims, 3 ready tickets. One refill run gave 3 runs.
    assert usage.runs_to_start(40, 17, 3, False, hi=8, refill=3) == 6
    assert usage.runs_to_start(40, 17, 0, False, hi=8, refill=3) == 3
    assert usage.runs_to_start(40, 38, 0, False, hi=8, refill=3) == 2              # not above the target
    assert usage.runs_to_start(40, 17, 30, False, hi=8, refill=3) == 8             # many ready: the cycle limit


def test_lane_plan_adds_the_refill_runs_to_the_opus_runs():
    assert usage.lane_plan(40, 17, 3, 0, 0.25, False, hi=8, refill=3) == (6, 0)
    assert usage.lane_plan(40, 17, 3, 2, 0.25, False, hi=8, refill=3) == (6, 2)    # 2 Haiku runs, 1 + 3 Opus runs
    assert usage.lane_plan(40, 17, 3, 0, 0.25, True, hi=8, refill=3) == (0, 0)
