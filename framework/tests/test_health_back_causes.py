"""health.back_causes and the `checked` result: a check with findings is no lost ticket, and repeats show (#5782)."""
import health
import report


def test_checked_is_a_result_and_no_given_back_ticket():
    assert report.result("Checked") == "checked"
    comments = [{"body": "Metrics: ticket #5 · size:S · checked · 9 min · setup 0 min · checks 1\n"
                         "Metrics: ticket #6 · size:S · none · 4 min · setup 0 min · checks 0"}]
    assert health.given_back(comments) == {"none": 1}
    assert health.back_causes(comments) == (1, {})


def test_back_causes_lists_the_tickets_of_two_or_more_runs():
    line = "Metrics: ticket #{} · size:S · {} · 5 min · setup 0 min · checks 0"
    comments = [{"body": line.format(n, r)} for n, r in
                [(7, "blocked"), (7, "checked"), (7, "none"), (8, "needs-human"), (8, "none"), (9, "none"),
                 (10, "pr #11"), (10, "none")]]
    assert health.back_causes(comments) == (1, {7: 3, 8: 2})
    assert health.back_causes([{"body": None}]) == (0, {})
