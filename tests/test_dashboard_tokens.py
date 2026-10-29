"""The chart "Usage per merged PR" of the dashboard: the `Tokens:` and `Metrics:` lines of each run report (owner,
2026-10-29)."""
import os

import dashboard_data as dd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = ("Tokens: 0.95M eq · calls 74 · write 0.11M · read 6.16M · out 0.02M · cost $2.56 · peak 119k · base 43k (repo 8k)"
       " · verify wait 10.6m 5x · force 0 · sinks base 40%, output 12%, Bash sed 6%")
TWO = ("Metrics: ticket #3506 · size:S · pr #3642 · 0 min · setup 1 min\n"
       "Metrics: ticket #3636 · size:M · merged · 0 min · setup 0 min\n"
       "Metrics: ticket #3400 · size:M · none · 23 min · setup 2 min\n")


def test_tokens_reads_the_cost_and_the_prs_of_each_report():
    comments = [{"created_at": "2026-10-29T08:55:53Z", "body": f"Did #3636.\n{TWO}{TOK}\n"},
                {"created_at": "2026-10-29T07:00:00Z", "body": TOK.replace("sinks base 40%", "sinks output 12%")},
                {"created_at": "2026-10-29T07:30:00Z", "body": "Usage: no Tokens line"}]
    assert dd.tokens(comments=comments) == [
        dict(at="2026-10-29T07:00:00Z", eq=0.95, calls=74, peak=119, base=None, prs=0),
        dict(at="2026-10-29T08:55:53Z", eq=0.95, calls=74, peak=119, base=0.40, prs=2)]


def test_the_page_reads_the_columns_of_the_tokens_file():
    page = open(os.path.join(ROOT, "tools", "dashboard_artifact", "index.html")).read()
    assert dd.page_columns(page)["tokens"] == {"at", "eq", "prs", "base"}
    assert 'id="per-pr-chart" data-source="per_pr"' in page and "drawPerPr();" in page
