"""tools/ship_pr.py runs only the test files of the change, never the full fast suite: CI runs it (owner, #4187)."""
import subprocess

import ship_pr as ship


def git(d, *args):
    return subprocess.run(["git", *args], cwd=d, capture_output=True, text=True)


def branch(tmp_path):
    """A clone on branch `side` that changes `lib.py` and adds `tests/test_new.py`; main has the tests of lib and other."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    for k, v in (("user.name", "t"), ("user.email", "t@t")):
        git(work, "config", k, v)
    (work / "tests").mkdir()
    (work / "lib.py").write_text("A = 1\n")
    (work / "tests/test_lib.py").write_text("import lib\n")
    (work / "tests/test_other.py").write_text("import other\n")
    git(work, "add", ".")
    git(work, "commit", "-qm", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    git(work, "checkout", "-qb", "side")
    (work / "lib.py").write_text("A = 2\n")
    (work / "tests/test_new.py").write_text("def test_x():\n    pass\n")
    git(work, "add", ".")
    git(work, "commit", "-qm", "change")
    return work


def runs(monkeypatch):
    calls = []
    real = subprocess.run

    def run(cmd, *a, **k):
        if cmd[0] == "git":
            return real(cmd, *a, **k)
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "1 passed (exit 0)\n", "")
    monkeypatch.setattr(ship.subprocess, "run", run)
    return calls


def test_the_checks_run_the_test_files_of_the_change_only(tmp_path, monkeypatch):
    monkeypatch.chdir(branch(tmp_path))
    calls = runs(monkeypatch)
    assert ship.checks()
    pytest = next(c for c in calls if "pytest" in c)
    assert sorted(f for f in pytest if f.startswith("tests/")) == ["tests/test_lib.py", "tests/test_new.py"]


def test_no_test_file_of_the_change_runs_no_tests(tmp_path, monkeypatch):
    work = branch(tmp_path)
    monkeypatch.chdir(work)
    git(work, "reset", "-q", "--hard", "origin/main")
    (work / "notes.md").write_text("x\n")
    git(work, "add", "notes.md")
    git(work, "commit", "-qm", "docs")
    calls = runs(monkeypatch)
    assert ship.checks()
    assert not [c for c in calls if "pytest" in c]
