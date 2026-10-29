"""guard-shell.sh blocks a run of the full fast suite: the quick CI runs it (owner, #4187)."""
import pytest

from test_guard_shell import run


@pytest.mark.parametrize("command", [
    "python3 -m pytest",
    "python3 -m pytest -n auto",
    "python3 -m pytest -q -n auto 2>&1 | tail -3",
    "cd /x && timeout 580 python3 -m pytest -q > out.txt",
    "python3 -m pytest tests/",
    "pytest -x",
])
def test_blocks_the_full_suite(command):
    assert run(command) == 2, command


@pytest.mark.parametrize("command", [
    "python3 -m pytest tests/test_a.py tests/test_b.py",
    "python3 -m pytest -q tests/test_a.py::test_x 2>&1 | tail -3",
    "python3 -m pytest -m slow",
    "python3 -m pytest -k ship_pr",
    "grep -l pytest tests/*.py",
    "F=$(grep -l X tests/*.py); python3 -m pytest -q $F",
    "grep -l X tests/*.py | xargs python3 -m pytest -q",
    "python3 tools/report.py --text 'ran python3 -m pytest'",
])
def test_allows_test_files_and_markers(command):
    assert run(command) == 0, command
