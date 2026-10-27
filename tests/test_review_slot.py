"""The process review starts by a time slot lock with back-off (#898): `claim.py 0 --review`, `--reviewed`."""
from test_claim import clones, tool  # noqa: F401

import claim

T = 1793000000                                                                  # 2026-10-26 07:33:20 UTC
BODY = 'Dashboard\n<!-- agent-state: {"last_run": "2026-10-26T07:00:00Z", "runs": 150} -->\n### Process changes\n'


def test_the_review_lock_of_a_slot_wins_once(clones):                          # noqa: F811
    a, b, _ = clones
    assert tool(a, "0", "--review").returncode == 0                             # a local remote: no state, 45 min
    assert tool(b, "0", "--review").returncode == 1                             # the same slot
    assert tool(a, "0", "--roadmap").returncode == 0 and tool(b, "0", "--roadmap").returncode == 1


def test_slots_of_45_minutes():
    keys = {claim.review_slot({}, T + m * 60) for m in range(0, 180)}
    assert len(keys) in (4, 5) and claim.review_slot({}, T) == claim.review_slot({}, T + 60)


def test_no_review_within_one_slot_length_after_the_last():
    state = {"review_minutes": 90, "last_review": "2026-10-26T07:00:00Z"}
    assert claim.review_slot(state, T) is None                                  # 33 minutes after the last
    assert claim.review_slot(state, T + 3600).startswith("90m-")                # 93 minutes after the last


def test_no_change_doubles_the_slot_and_a_change_resets_it():
    body = claim.reviewed(BODY, False, T)
    state = claim.agent_state(body)
    assert state == {"last_run": "2026-10-26T07:00:00Z", "runs": 150, "last_review": "2026-10-26T07:33:20Z",
                     "review_minutes": 90}
    assert body.startswith("Dashboard\n<!-- agent-state: ") and body.endswith("### Process changes\n")
    for want in (120, 120):                                                    # REVIEW_MAX (#1697)
        body = claim.reviewed(body, False, T)
        assert claim.agent_state(body)["review_minutes"] == want
    assert claim.agent_state(claim.reviewed(body, True, T))["review_minutes"] == 45
