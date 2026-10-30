"""tools/dashboard_data.py `reviews`: the process reviews and the merged PRs between them, for the tab "Improvements"
of the dashboard (#4347)."""
import dashboard_data


def comment(at, body):
    return {"created_at": at, "body": body}


def test_each_review_counts_the_merges_since_the_review_before_it():
    merges = [{"merged_at": t} for t in ("2026-10-01T01:00:00Z", "2026-10-01T02:00:00Z", "2026-10-01T03:00:00Z")]
    comments = [comment("2026-10-01T02:30:00Z", "Process review (run 2): PR #12 and PR #7.\n\n- Numbers"),
                comment("2026-10-01T00:30:00Z", "Process review (run 1).\n\nmore"),
                comment("2026-10-01T01:30:00Z", "A ticket report, no review: PR #9")]
    rows = dashboard_data.reviews(merges, comments=comments)
    assert [(r["at"], r["prs"], r["changes"]) for r in rows] == [
        ("2026-10-01T00:30:00Z", None, []), ("2026-10-01T02:30:00Z", 2, [7, 12])]
    assert rows[1]["text"] == "Process review (run 2): PR #12 and PR #7."


def test_a_long_report_is_cut_to_400_characters():
    row, = dashboard_data.reviews([], comments=[comment("2026-10-01T00:00:00Z", "Process review " + "x" * 500)])
    assert len(row["text"]) == 400 and row["text"].endswith("...")


def test_the_page_has_the_tab_and_reads_the_data_file():
    page = open(dashboard_data.os.path.join(dashboard_data.os.path.dirname(__file__), "..", "tools",
                                            "dashboard_artifact", "index.html")).read()
    assert 'data-page="improvements"' in page and "reviews" in dashboard_data.page_columns(page)
