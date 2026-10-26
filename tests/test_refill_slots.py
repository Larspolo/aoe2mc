"""The whole-queue refill lock changes each 10 minutes, so that about 10 runs find tickets (#650)."""
import claim

T = 1793000000                                                                  # 2026-10-26 07:33:20 UTC


def test_six_refill_slots_per_hour():
    slots = {claim.refill_state(0, now=T - 2000 + m * 60) for m in range(60)}   # 07:00 to 07:59
    assert len(slots) == 6
    assert claim.refill_state(0, now=T) == claim.refill_state(0, now=T + 340)   # 07:39: the same slot
    assert claim.refill_state(0, now=T) != claim.refill_state(0, now=T + 400)   # 07:40: the next slot
