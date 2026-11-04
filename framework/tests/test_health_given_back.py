"""health.given_back: the tickets that runs gave back, from the results of the Metrics lines (#5649)."""
import health


def test_given_back_counts_the_results_of_the_run_reports():
    comments = [{"body": "Run X.\n\nMetrics: ticket #5 · size:S · none · 9 min · setup 2 min · checks 0\n"
                         "Metrics: ticket #6 · size:M · pr #7 · 12 min · setup 0 min · checks 1"},
                {"body": "Metrics: ticket #8 · size:S · blocked · 30 min · setup 0 min · checks 2"},
                {"body": "Metrics: ticket #9 · size:S · needs-human · 5 min · setup 0 min · checks 0\n"
                         "Metrics: ticket #10 · size:S · closed · 3 min · setup 0 min · checks 0\n"
                         "Metrics: ticket #11 · size:S · none · 4 min · setup 0 min · checks 0"},
                {"body": None}]
    assert health.given_back(comments) == {"none": 2, "blocked": 1, "needs-human": 1}


def test_a_comment_of_a_release_workflow_is_no_release():
    comments = [{"body": "Released by the After release workflow (`v0.1.0`, #4175). It waits with `rank`."},
                {"body": "Released by the Release workflow: tag `v0.1.0` on `d8318c6`."}]
    assert health.given_back(comments) == {}
    assert "releases" not in health.events(comments)
