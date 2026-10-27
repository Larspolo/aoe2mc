"""tools/merge_jsonl.py merges the lines of a JSON lines table by name, not by union (#2004)."""
import json
import os
import subprocess
import sys

import merge_jsonl

TOOL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "merge_jsonl.py"))


def line(name, **kw):
    return json.dumps({"name": name, **kw}) + "\n"


BASE = [line("AZTECS", missing=["A"]), line("BRITONS", missing=["A"]), line("CELTS", missing=["A"])]


def git(d, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          cwd=d, capture_output=True, text=True)


def merged(tmp_path, ours, theirs):
    """(exit code of git merge, lines of the file): a real git merge with the driver of the hook."""
    d = str(tmp_path)
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "merge.jsonl.driver", f"{sys.executable} {TOOL} %O %A %B")
    open(os.path.join(d, ".gitattributes"), "w").write("*.jsonl merge=jsonl\n")
    path = os.path.join(d, "civs.jsonl")
    for branch, lines in (("main", BASE), ("ours", ours), ("theirs", theirs)):
        if branch != "main":
            git(d, "checkout", "-q", "-b", branch, "main")
        open(path, "w").writelines(lines)
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", branch)
    git(d, "checkout", "-q", "ours")
    rc = git(d, "merge", "-q", "--no-edit", "theirs").returncode
    return rc, open(path).readlines()


def test_changes_of_different_lines_give_one_line_per_name(tmp_path):
    ours = [BASE[0], line("BRITONS", missing=["A", "B"]), BASE[2]]
    theirs = [BASE[0], BASE[1], line("CELTS", missing=[]), line("DUTCH", missing=["C"])]
    rc, lines = merged(tmp_path, ours, theirs)
    assert rc == 0
    assert lines == [BASE[0], ours[1], theirs[2], theirs[3]]


def test_a_line_changed_on_both_sides_is_a_conflict(tmp_path):
    ours = [BASE[0], line("BRITONS", missing=["A"], wonder="B"), BASE[2]]     # one key, two values: lists merge
    theirs = [BASE[0], line("BRITONS", missing=["A"], wonder="C"), BASE[2]]
    rc, lines = merged(tmp_path, ours, theirs)
    assert rc != 0
    assert lines == [BASE[0], "<<<<<<< ours\n", ours[1], "=======\n", theirs[1], ">>>>>>> theirs\n", BASE[2]]


def test_the_same_change_on_both_sides_and_deletes():
    same = line("BRITONS", missing=[])
    lines, conflicts = merge_jsonl.merge(*(merge_jsonl.rows_of(x) for x in (
        BASE, [BASE[0], same], [same, BASE[2]])))
    assert (lines, conflicts) == ([same], 0)              # AZTECS deleted by theirs, CELTS by ours


def test_new_lines_of_theirs_stay_below_their_neighbour():
    ours = BASE + [line("DUTCH")]
    theirs = [BASE[0], line("ARMENIANS"), BASE[1], BASE[2]]
    lines, conflicts = merge_jsonl.merge(*(merge_jsonl.rows_of(x) for x in (BASE, ours, theirs)))
    assert lines == [BASE[0], theirs[1], BASE[1], BASE[2], ours[3]] and conflicts == 0


def test_the_session_start_hook_registers_the_driver():
    root = os.path.join(os.path.dirname(TOOL), "..")
    assert "merge.jsonl.driver" in open(os.path.join(root, ".claude", "hooks", "session-start.sh")).read()
