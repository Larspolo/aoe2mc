"""No tracked text file holds a git conflict marker (#2928). A marker in a docstring or a comment
runs with no error: Python reads it as text, so the tests pass and the marker merges into main."""
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKERS = ("<<<<<<< ", ">>>>>>> ")


def markers(path):
    """The line numbers of the conflict markers of one file. Only text files; a marker must start a line."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    return [i for i, line in enumerate(lines, 1) if line.startswith(MARKERS) or line == "======="]


def tracked_files():
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    return [os.path.join(ROOT, p) for p in out.split("\0") if p]


def test_no_conflict_marker_in_tracked_files():
    found = {os.path.relpath(p, ROOT): markers(p) for p in tracked_files()}
    found = {name: lines for name, lines in found.items() if lines}
    assert found == {}, "conflict markers (file: line numbers): %s" % found


def test_marker_is_found_with_its_line(tmp_path):
    path = tmp_path / "doc.py"
    path.write_text('"""Doc.\n<<<<<<< HEAD\nText.\n=======\nOther.\n>>>>>>> origin/main\n"""\n', encoding="utf-8")
    assert markers(str(path)) == [2, 4, 6]


@pytest.mark.parametrize("text", ["x = 1  # <<<<<<< HEAD\n", "    <<<<<<< HEAD\n", "a = '======='\n"])
def test_marker_inside_a_line_is_not_found(tmp_path, text):
    path = tmp_path / "code.py"
    path.write_text(text, encoding="utf-8")
    assert markers(str(path)) == []
