"""`tokens.phases()` and `run_data()`: an adopted claim (`claim.py N --adopt CLAIM`, the brief of the pacer) is a won
claim (#5622)."""
import tokens


def at(s):
    return f"2026-11-01T10:{s // 60:02d}:{s % 60:02d}Z"


def call(i, s, cmd):
    return {"type": "assistant", "timestamp": at(s),
            "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": cmd}}]}}


def result(i, s, text):
    return {"type": "user", "timestamp": at(s),
            "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": text}]}}


RECORDS = [call(1, 0, "python3 framework/tools/claim.py 7 --adopt pacer-r1a2b"),
           result(1, 2, "adopted claim/7: #7 is yours"),
           call(2, 62, "cat a.py"), result(2, 63, "ok"),
           call(3, 120, "python3 framework/tools/claim.py 8"), result(3, 122, "claimed claim/8"),
           call(4, 240, "cat b.py"), result(4, 241, "ok")]


def test_the_adopted_ticket_and_the_next_ticket_get_their_own_minutes():
    out = tokens.phases(RECORDS)
    assert list(out) == [7, 8]
    assert round(sum(out[7].values()) * 60) == 63      # the gap before the next claim counts for it (#5528)
    assert round(sum(out[8].values()) * 60) == 57 + 2 + 118 + 1


def test_a_failed_adopt_is_no_claim():
    rec = [call(1, 0, "python3 framework/tools/claim.py 7 --adopt pacer-r1a2b"),
           result(1, 2, "#7: the beat failed, follow the skill without the brief")]
    assert list(tokens.phases(rec)) == [None]


def test_run_data_starts_the_setup_at_the_adopt():
    assert tokens.run_data(RECORDS)["setup"] is not None
