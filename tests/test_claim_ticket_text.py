"""tools/claim.py: a won claim prints the ticket and its comments, so that the run needs no extra API call (#3459)."""
import claim


def test_the_ticket_text_has_the_body_and_the_comments_but_no_claim_comments():
    issue = {"number": 7, "title": "Fix it", "body": "## Goal\nFix it.\n"}
    comments = [{"user": {"login": "Larspolo"}, "created_at": "2026-10-28T22:00:00Z", "body": "Do X first."},
                {"user": {"login": "Larspolo"}, "created_at": "2026-10-28T22:01:00Z", "body": "Started by `b`."},
                {"user": {"login": "Larspolo"}, "created_at": "2026-10-28T22:02:00Z", "body": "Taken over by `c`: stuck."}]
    text = claim.ticket_text(issue, comments)
    assert text.startswith("#7 Fix it\n## Goal\nFix it.")
    assert "comment of Larspolo (2026-10-28T22:00:00Z):\nDo X first." in text
    assert "Started by" not in text and "Taken over" not in text


def test_the_calls_of_a_transcript_by_phase_label_and_pair():
    import tokens
    rec = lambda tid, cmd: {"type": "assistant", "message": {"id": tid, "content": [
        {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd}}]}}
    ph, lab, pairs = tokens.calls([rec("a", "python3 tools/claim.py 5"), rec("b", "gh api repos/x/issues/5"),
                                   rec("c", "python3 tools/claim.py 6"), rec("d", "gh api repos/x/issues/6")])
    assert ph["claim"] == 2 and sum(ph.values()) == 4
    assert lab["Bash claim.py"] == 2 and pairs[("Bash claim.py", "Bash gh api")] == 2
