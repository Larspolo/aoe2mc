"""framework/tools/ship_pr.py runs the data format tests when the change has a module of tests/data_checks/ (#4778): no
import of a test_*.py file names it."""
import ship_pr as ship
from test_ship_pr_data import data_branch, pytest_files
from test_ship_pr_scope import git


def test_a_change_of_a_data_check_runs_the_data_tests(tmp_path, monkeypatch):
    work = data_branch(tmp_path, "notes.txt")
    (work / ship.DATA_CHECKS).mkdir()
    (work / ship.DATA_CHECKS / "units.py").write_text("def check(row):\n    pass\n")
    git(work, "add", ".")
    git(work, "commit", "-qm", "check")
    monkeypatch.chdir(work)
    assert pytest_files(monkeypatch) == sorted(ship.DATA_TESTS)
