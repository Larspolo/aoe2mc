"""The refresh checks the columns of the new data files against the page, without the old assets (#1031)."""
import json
import os

import dashboard_data as dd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = open(os.path.join(ROOT, "tools", "dashboard_artifact", "index.html")).read()

TOY = """
<table id="t" data-source="setup"><thead><tr><th data-field="part">P</th><th data-field="does">D</th></tr></thead></table>
<script>
dash.calc('a', {
  inputs: ['tickets', 'merges'],
  fn: (tickets, merges) => {
    const open = tickets.filter((r) => r.state === 'open')
      .sort((a, b) => a.number - b.number);
    const n = open.filter((r) => r.needs_human).length;
    const m = merges.map((r) => ({ at: r.merged_at })).filter((x) => x.not_a_column);
    return tickets.reduce((s, t) => s + t.ignored, 0) + n + m.length;
  },
});
function drawUsage() {
    const d = dash.data('usage');
    const pts = d.data.map((r) => ({ t: r.at, u: r.usage }));
}
</script>
"""


def test_page_columns_follow_filters_aliases_and_tables():
    cols = dd.page_columns(TOY)
    assert cols["tickets"] == {"state", "number", "needs_human"}
    assert cols["merges"] == {"merged_at"} and cols["usage"] == {"at", "usage"}
    assert cols["setup"] == {"part", "does"} and cols["epics"] == set()


def test_the_real_page_reads_columns_that_the_data_files_have():
    cols = dd.page_columns(PAGE)
    assert {"created_at", "closed_at", "priority", "in_progress", "muted"} <= cols["tickets"]
    assert {"merged_at", "minutes_open"} <= cols["merges"] and {"at", "usage", "resets", "runs", "haiku", "week", "week_resets"} == cols["usage"]
    assert {"key", "subs_total"} <= cols["epics"] and {"kind", "share", "estimate"} <= cols["release_bar"]


def test_check_names_the_missing_columns(tmp_path):
    rows = {"tickets": [{"state": "open", "number": 1}], "merges": [{"merged_at": "x"}], "usage": [],
            "setup": [{"part": "p", "does": "d"}]}
    for name, file in dd.DATASETS.items():
        json.dump(rows.get(name, []), open(tmp_path / file, "w"))
    assert dd.check(str(tmp_path), TOY) == [("aoe2mc-tickets.json", ["needs_human"])]


def test_main_checks_the_columns_and_fails_on_a_missing_one(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dd, "pages", lambda path: [])
    monkeypatch.setattr(dd, "usage", lambda: [])
    monkeypatch.setattr(dd, "tokens", lambda: [])
    monkeypatch.setattr(dd, "reviews", lambda merges: [])
    assert dd.main(str(tmp_path)) == 0 and "columns: OK" in capsys.readouterr().out
    monkeypatch.setattr(dd, "tickets", lambda issues: [{"number": 1}])
    assert dd.main(str(tmp_path)) == 1
    assert "aoe2mc-tickets.json: the page reads missing columns: closed_at" in capsys.readouterr().out
