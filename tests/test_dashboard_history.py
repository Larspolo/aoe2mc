"""The owner's dashboard shows the progress of each roadmap item and goal over time."""
import os
import re

import dashboard_data as dd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = open(os.path.join(ROOT, "tools", "dashboard_artifact", "index.html")).read()
PROGRESS = PAGE[PAGE.index('<section class="ax-page" id="progress"'):PAGE.index('<section class="ax-page" id="tickets"')]


def issue(number, **kw):
    return dict(number=number, title="T", state="open", created_at="2026-10-27T10:00:00Z", closed_at=None, labels=[], **kw)


def test_tickets_name_the_epic_of_a_sub_issue():
    rows = dd.tickets([issue(5), issue(6, parent_issue_url="https://api.github.com/repos/Larspolo/aoe2mc/issues/5")])
    assert [r["parent"] for r in rows] == [None, 5]


def test_the_history_reads_the_parent_and_the_times_of_the_tickets():
    cols = dd.page_columns(PAGE)
    assert {"parent", "created_at", "closed_at", "number"} <= cols["tickets"]


def test_each_release_table_has_a_progress_graph():
    tables = re.findall(r'<table[^>]*id="release-(\w+)".*?</table>', PROGRESS, re.S)
    assert tables == ["convert", "play", "replay", "system"]
    assert PROGRESS.count('<th data-field="progress">Progress</th>') == 4
    assert "['progress', (v, r) => progressGraph(byItem.get(r.id)" in PAGE
    assert "dash.calc('release_history'" in PAGE and "dash.calc('goal_history'" in PAGE
    assert 'id="history-chart" data-source="goal_history"' in PROGRESS


def test_each_goal_card_closes_before_the_next():
    # The replay card had no end tag, so the system card was inside it.
    depth = 0
    for m in re.finditer(r"<(/?)div\b", PROGRESS):
        depth += -1 if m[1] else 1
        if PROGRESS.startswith('<div class="ax-card" id="goal-', m.start()):
            assert depth == 1, PROGRESS[m.start():m.start() + 40]
    assert depth == 0
