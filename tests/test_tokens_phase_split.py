"""`tokens.phases()`: the gap after a tool result counts for the phase of the next call, the run of a tool for its
own phase (#5528)."""
import tokens


def at(s):
    return f"2026-11-01T10:{s // 60:02d}:{s % 60:02d}Z"


def call(i, s, name, inp):
    return {"type": "assistant", "timestamp": at(s),
            "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}}


def result(i, s, text="ok"):
    return {"type": "user", "timestamp": at(s),
            "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": text}]}}


def test_the_pause_before_an_edit_is_code_and_a_slow_pytest_is_verify():
    records = [call(1, 0, "Read", {"file_path": "aoe2mc.py"}), result(1, 6),
               call(2, 306, "Edit", {"file_path": "aoe2mc.py"}), result(2, 307),        # 5 minutes to write the edit
               call(3, 327, "Bash", {"command": "python3 -m pytest tests/test_x.py"}), result(3, 627),
               call(4, 633, "Read", {"file_path": "aoe2mc.py"})]
    m = tokens.phases(records)[None]
    assert round(m["read"] * 60) == 6 + 6
    assert round(m["code"] * 60) == 300 + 1
    assert round(m["verify"] * 60) == 20 + 300


def test_no_result_keeps_the_whole_gap_and_a_claim_starts_its_ticket():
    claim = "python3 framework/tools/claim.py 7"
    records = [call(1, 0, "Read", {"file_path": "a.py"}),
               call(2, 60, "Bash", {"command": claim}), result(2, 62, "claimed claim/7"),
               call(3, 182, "Edit", {"file_path": "a.py"})]
    out = tokens.phases(records)
    assert list(out) == [7]
    assert round(out[7]["read"] * 60) == 60
    assert round(out[7]["claim"] * 60) == 2
    assert round(out[7]["code"] * 60) == 120
