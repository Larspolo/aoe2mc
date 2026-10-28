import report


def test_a_report_counts_the_run_and_keeps_the_other_state():
    body = '<!-- agent-state: {"last_run": "2026-10-27T00:00:00Z", "runs": 41, "review_prs": 50} -->\n## Agent status\n'
    out = report.counted(body, now=1793167200)
    assert report.agent_state(out) == {"last_run": "2026-10-28T06:00:00Z", "runs": 42, "review_prs": 50}
    assert out.endswith("## Agent status\n")


def test_a_body_without_state_gets_one():
    out = report.counted("## Agent status", now=1793167200)
    assert report.agent_state(out) == {"last_run": "2026-10-28T06:00:00Z", "runs": 1}
