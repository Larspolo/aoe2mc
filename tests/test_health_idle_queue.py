"""framework/tools/health.py: the idle queue, the pacer ran with a target above 0 but no claim and no start (#5199)."""
import datetime

import health

UNTIL = datetime.datetime(2026, 10, 31, 18, 0, tzinfo=datetime.timezone.utc)


def cycle(hm, target=36, claims=0, started=0, paused=False):
    return {"at": f"2026-10-31T{hm}:00Z", "target": target, "claims": claims,
            "started": {"main": started, "haiku": 0, "deep": 0}, "line": f"paused {paused}"}


def test_no_idle_cycle():
    cycles = [cycle("14:00", claims=2), cycle("14:10", started=1), cycle("14:20", target=0), cycle("14:30", paused=True)]
    assert health.idle_queue(cycles, UNTIL) == (0.0, 0.0)


def test_one_stretch_lasts_to_the_next_busy_cycle():
    cycles = [cycle("14:00", claims=1), cycle("14:10"), cycle("14:20"), cycle("15:40", started=1)]
    assert health.idle_queue(cycles, UNTIL) == (1.5, 1.5)


def test_two_stretches_and_an_open_one_to_the_end():
    cycles = [cycle("12:00"), cycle("13:00", claims=1), cycle("16:00"), cycle("16:30")]
    longest, total = health.idle_queue(cycles, UNTIL)
    assert (longest, total) == (2.0, 3.0)


def test_report_prints_the_line():
    line = "Idle queue (target > 0, no claim, no start): longest 2.0 h, sum 3.0 h"
    text = health.report(UNTIL, [], [], [], [], [], [], idle=(2.0, 3.0))
    assert line in text
