"""The "Usage" tab of the dashboard (owner, 2026-11-01): the usage of each run per lane and type of work over time, and
its split by phase and by sink."""
import os

import dashboard_data as dd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = ("Tokens: 2.00M eq · calls 74 · write 0.11M · read 6.16M · out 0.02M · cost $4.00 · peak 119k · base 43k (repo 8k)"
       " · force 0 · sinks base 40%, Bash sed 10%")
RUN = "Run: abc · branch b · start 2026-10-30T07:00:00Z · wall 20 min · eq read 0.30M, code 0.10M, verify 0.00M · lane haiku"
TWO = ("Metrics: ticket #1 · size:S · merged · 0 min · setup 1 min\n"
       "Metrics: ticket #2 · size:M · none · 23 min · setup 2 min\n")


def test_spend_splits_a_run_by_ticket_type_phase_and_sink():
    rows = dd.spend(comments=[{"created_at": "2026-10-30T08:00:00Z", "body": f"Did it.\n{TWO}{TOK}\n{RUN}\n"}],
                    process=[2])
    assert [(r["lane"], r["kind"], r["runs"], r["eq"], r["cost"]) for r in rows] == [
        ("haiku", "S", 0.5, 1.0, 2.0), ("haiku", "improve", 0.5, 1.0, 2.0)]
    assert rows[0]["phases"] == {"read": 0.75, "code": 0.25}
    assert rows[0]["sinks"] == {"base": 0.4, "Bash sed": 0.1, "other": 0.5}


def test_spend_prefers_the_fields_of_a_run_record_and_names_runs_without_a_ticket():
    record = {"created_at": "2026-10-30T09:00:00Z", "body": TOK, "lane": "deep",
              "tokens": {"phases_eq": {"read": 1e6, "ci": 3e6}, "sinks": {"base": 0.5, "output": 0.5}}}
    review = {"created_at": "2026-10-30T10:00:00Z", "body": f"Process review: no change.\n{TOK}"}
    rows = dd.spend(comments=[record, review, {"created_at": "2026-10-30T11:00:00Z", "body": TWO}])
    assert [(r["lane"], r["kind"]) for r in rows] == [("deep", "no ticket"), ("opus", "review")]
    assert rows[0]["phases"] == {"read": 0.5, "ci": 1.5} and rows[0]["sinks"] == {"base": 1.0, "output": 1.0}


def test_the_usage_tab_reads_the_columns_of_the_spend_file():
    page = open(os.path.join(ROOT, "tools", "dashboard_artifact", "index.html")).read()
    assert dd.page_columns(page)["spend"] == {"at", "lane", "kind", "runs", "eq", "cost", "phases", "sinks"}
    assert 'data-page="spend"' in page and "drawSpend(); drawSpendSplit();" in page
