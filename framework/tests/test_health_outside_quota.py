"""The health report shows the 5-hour quota that was used while no run worked (#6104): on 2026-11-06 the window went
from 13 % to 31 % in 3 hours with no claim and no start, and "Quota per merged PR" counted it against the runs."""
import datetime

import health

UNTIL = datetime.datetime(2026, 11, 4, 14, 0, tzinfo=datetime.timezone.utc)
RESET = 1794009600


def cycle(at, used, claims=0, started=0, reset=RESET):
    return {"at": f"2026-11-04T{at}:00Z", "target": 8, "claims": claims, "ready": 0, "refill": 0,
            "started": {"deep": started}, "five_hour": [used, reset, "allowed"], "line": "paused False"}


def test_the_rise_between_two_cycles_with_no_run():
    cycles = [cycle("10:00", 0.10), cycle("11:00", 0.15), cycle("12:00", 0.18)]
    assert round(health.outside_quota(cycles), 3) == 0.08


def test_a_claim_a_start_or_a_new_window_counts_nothing():
    cycles = [cycle("09:00", 0.05, started=1), cycle("10:00", 0.10), cycle("11:00", 0.20, claims=1),
              cycle("12:00", 0.25), cycle("13:00", 0.01, reset=RESET + 18000), cycle("13:30", 0.02, reset=RESET + 18000)]
    assert round(health.outside_quota(cycles), 3) == 0.01
    assert health.outside_quota([{"at": "2026-11-04T10:00:00Z"}, {"at": "2026-11-04T11:00:00Z"}]) == 0


def test_the_idle_line_names_the_quota_with_no_run():
    out = health.report(UNTIL, [], [], [], [], [], [], idle=(3.0, 3.0, 2.0, 0.18))
    assert "(no work: 2.0 h, #854) · quota with no run: 18% of the 5-hour window (#6104)" in out
    assert "(no work: 2.0 h, #854)" in health.report(UNTIL, [], [], [], [], [], [], idle=(3.0, 3.0, 2.0))
