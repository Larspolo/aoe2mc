"""The queue refills often enough: a refill lock each 15 minutes, and a refill run when no ticket is ready (#609)."""
import claim
import usage

T = 1793000000                                                                  # 2026-10-26 07:33:20 UTC


def test_the_whole_refill_lock_changes_with_its_slot():
    assert claim.refill_state(0, now=T) == claim.refill_state(0, now=T + 60)    # 07:34: the same lock
    assert claim.refill_state(0, now=T) != claim.refill_state(0, now=T + 900)   # 07:48: a new lock (#650: 10 minutes)
    assert claim.refill_state(0, now=T + 1600)[-1] == "0"                        # 08:00: the first slot


def test_a_refill_run_when_no_ticket_is_ready():
    assert usage.runs_to_start(target=6, claims=1, ready=0, paused=False) == usage.REFILL
    assert usage.runs_to_start(target=6, claims=6, ready=0, paused=False) == 0   # enough runs: one of them refills
    assert usage.runs_to_start(target=6, claims=1, ready=0, paused=True) == 0
