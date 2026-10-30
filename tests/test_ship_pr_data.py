"""framework/tools/ship_pr.py runs the data format tests when the change has a .jsonl file (#4614)."""
from test_ship_pr_scope import branch, git, runs

import ship_pr as ship


def data_branch(tmp_path, name):
    work = branch(tmp_path)
    for f in ship.DATA_TESTS:
        (work / f).write_text("def test_x():\n    pass\n")
    git(work, "add", ".")
    git(work, "commit", "-qm", "data tests")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    git(work, "checkout", "-qB", "data", "origin/main")
    (work / name).write_text('{"name": "a"}\n')
    git(work, "add", name)
    git(work, "commit", "-qm", "data")
    return work


def pytest_files(monkeypatch):
    calls = runs(monkeypatch)
    assert ship.checks()
    return sorted(f for c in calls if "pytest" in c for f in c if f.startswith("tests/"))


def test_a_jsonl_change_runs_the_data_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(data_branch(tmp_path, "civ.jsonl"))
    assert pytest_files(monkeypatch) == sorted(ship.DATA_TESTS)


def test_a_change_without_jsonl_runs_no_data_test(tmp_path, monkeypatch):
    monkeypatch.chdir(data_branch(tmp_path, "civ.json"))
    assert pytest_files(monkeypatch) == []
