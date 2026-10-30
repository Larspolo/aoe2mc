"""framework/tools/health.py names the test files that several conflicted PRs change: a count or a list of the data in a test
makes each new unit or building change the same line (miss #2008). The tests count the menu items from the data."""
import datetime

import health

SINCE = datetime.datetime(2026, 10, 25, 12, 0, tzinfo=datetime.timezone.utc)


def test_the_report_names_the_test_files_of_two_or_more_conflicted_prs():
    files_of = {7: ["game/train.py", "tests/test_krepost.py", "tests/test_a.py"], 9: ["tests/test_krepost.py"]}
    assert health.conflict_files(files_of, prefix="tests/") == [("tests/test_krepost.py", 2), ("tests/test_a.py", 1)]
    text = health.report(SINCE, [], [], [], [], [], [], files_of)
    assert "Test files of 2 or more conflicted PRs (PRs): tests/test_krepost.py 2" in text
    assert "Test files" not in health.report(SINCE, [], [], [], [], [], [], {7: ["tests/test_a.py"]})
