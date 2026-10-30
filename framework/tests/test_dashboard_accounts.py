"""The accounts of the dashboards (#4239): one row per Claude account in the site data and in the status body, and the
per-account quota of the pacer record. Test data only: two accounts with their `Usage:`, `Run:` and report lines."""
import datetime

import dashboard
import dashboard_data as dd
import pacer

NOW = datetime.datetime(2026, 10, 29, 12, tzinfo=datetime.timezone.utc)
RESET = "2026-10-30T02:00:00Z"


def report(account, used, runs, week, merged, eq):
    """One status comment: the `Usage:` line of the account, and its report with `Run:`, `Tokens:` and `Metrics:`."""
    usage = (f"Usage: 2026-10-29T11:00:00Z · usage {used}% · resets {RESET} · runs {runs} · week {week}% · "
             f"week resets 2026-10-30T04:00:00Z · account {account}")
    prs = "".join(f"Metrics: ticket #{n} · size:S · merged · 0 min · setup 0 min\n" for n in range(merged))
    run = f"Run: 2026-10-29 11:00 · 20 min · lane opus · account {account}"
    tokens = (f"Tokens: {eq}M eq · calls 74 · write 0.11M · read 6.16M · out 0.02M · cost $2.56 · peak 119k · "
              "base 43k (repo 8k) · verify wait 10.6m 5x · force 0 · sinks base 40%")
    return {"body": f"{usage}\n{prs}{tokens}\n{run}", "created_at": "2026-10-29T11:00:00Z"}


def comments():
    return [report("lars", 40.0, 12, 30.0, 2, 1.0), report("bob", 68.0, 27, 9.0, 4, 2.0),
            report("lars", 42.5, 14, 31.0, 1, 0.5)]


def test_each_account_has_one_row_with_its_last_usage_and_its_merged_prs():
    rows = {r["account"]: r for r in dd.accounts(comments=comments())}
    assert set(rows) == {"lars", "bob"}
    assert rows["lars"]["five_hour"] == 0.425 and rows["lars"]["runs"] == 14     # the last line of lars
    assert rows["bob"]["five_hour"] == 0.68 and rows["bob"]["week"] == 0.09
    assert rows["lars"]["merged"] == 3 and rows["bob"]["merged"] == 4


def test_the_tokens_per_merged_pr_divide_the_cost_of_the_reports_of_each_account():
    rows = {r["account"]: r for r in dd.accounts(comments=comments())}
    assert rows["lars"]["tokens_per_pr"] == 1.5 / 3                          # (1.0 + 0.5) M eq over 3 PRs
    assert rows["bob"]["tokens_per_pr"] == 2.0 / 4


def test_the_status_body_has_one_row_per_account_when_there_are_two():
    rows = dd.accounts(comments=comments())
    body = dashboard.render("", [], {}, [], [], [], NOW, [], [], accounts=rows)
    assert "### Accounts" in body
    assert "| bob | 68.0% | 9.0% | 27 | 4 | 0.50M |" in body
    assert "| lars | 42.5% | 31.0% | 14 | 3 | 0.50M |" in body


def test_one_account_keeps_the_body_as_it_was():
    one = dd.accounts(comments=[report("bob", 10.0, 3, 5.0, 1, 0.2)])
    assert "### Accounts" not in dashboard.render("", [], {}, [], [], [], NOW, [], [], accounts=one)
    assert "### Accounts" not in dashboard.render("", [], {}, [], [], [], NOW, [], [])


def test_the_pacer_record_holds_the_quota_of_each_account():
    found = {"five_hour": (0.5, NOW, 0)}
    quota = {"lars": {"five_hour": 0.4, "seven_day": 0.3, "missing": 2.5},
             "bob": {"five_hour": 0.68, "seven_day": None, "missing": None}}
    rec = pacer.record(NOW, found, 0.01, 0.002, 3, {}, {}, "", quota=quota)
    assert rec["quota"] == quota
    assert "quota" not in pacer.record(NOW, found, 0.01, 0.002, 3, {}, {}, "")
