"""Each data file has a line merge rule in .gitattributes (#2332, epic #1909): without one, git merges two new lines at
the end of the file as a conflict (game/data/taunts.jsonl had none)."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rules(paths):
    """{path: the merge attribute of .gitattributes, "unspecified" for none} (git check-attr reads the real rules)."""
    out = subprocess.run(["git", "check-attr", "merge", "--", *paths], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    return dict(line.rsplit(": merge: ", 1) for line in out.splitlines())


def test_each_data_file_has_a_merge_rule():
    paths = sorted(f"{d}/{n}" for d in ("data", "game/data") for n in os.listdir(os.path.join(ROOT, d))
                   if n.endswith(".jsonl"))
    assert "game/data/taunts.jsonl" in paths
    missing = [p for p, rule in rules(paths).items() if rule not in ("jsonl", "union")]
    assert not missing, f"add a merge rule to .gitattributes (merge=jsonl for a table with names): {missing}"


def test_the_check_finds_a_file_with_no_rule():
    assert rules(["game/data/new.jsonl"]) == {"game/data/new.jsonl": "unspecified"}
