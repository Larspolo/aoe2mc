"""The effect of the `next:` line of the briefs (#5308): the pacer records it, the report names the source of each
later ticket and each failed `next:` claim, and `health.py` counts them."""
import json
import pathlib

import claim
import health
import pacer
import pytest
import report

DATA = json.loads((pathlib.Path(__file__).parent / "data" / "next_effect.json").read_text())


def test_health_counts_next_runs_failed_claims_and_eq_per_ticket():
    took, failed, first, later = health.next_effect(DATA)
    assert (took, failed) == (1, 2)
    assert first == pytest.approx(0.35)                 # 0.2, 0.4, 0.4 (0.8 / 2), 0.3 (0.9 / 3)
    assert later == pytest.approx(0.3)                  # 0.4, 0.3, 0.3


def test_health_with_no_reports_gives_none():
    assert health.next_effect([]) == (0, 0, None, None)


def test_metrics_line_names_the_source_and_the_failed_claims():
    line = report.metrics(4, "S", "pr #14", 20, source="next")
    assert line.endswith("· source next")
    assert health.next_effect([{"body": line + "\n" + report.next_failed([5]) + "\nTokens: 1M eq · x · sinks none"}])[:2] == (1, 1)
    assert report.next_failed([]) is None


def test_report_rejects_a_bad_source():
    with pytest.raises(SystemExit):
        report.main(["--text", "t", "--usage", "u", "--ticket", "1", "--size", "S", "--result", "pr #2",
                     "--ticket", "3", "--size", "S", "--result", "pr #4", "--source", "next", "--source", "next", "--source", "x"])


def test_briefs_keep_the_next_tickets_of_each_started_run(monkeypatch):
    b = pacer.Briefs(None, {}, 0, {})
    monkeypatch.setattr(b, "take", lambda task, account=None: (7, "pacer-r1", "brief", [8, 9]))
    monkeypatch.setattr(pacer, "send", lambda *a: {})
    monkeypatch.setattr(claim, "start", lambda *a, **k: None)
    b.start("main", "url", "token")
    assert b.given == [7] and b.next == {7: [8, 9]}
