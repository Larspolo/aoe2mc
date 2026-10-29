"""tests/data/civ_bonuses.jsonl merges by line (#2100): two tickets that close two neighbouring bonuses of one
civilization give no conflict. A real git merge with the driver and the line of .gitattributes."""
import json
import os
import subprocess
import sys

from test_merge_jsonl import TOOL, git

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join("tests", "data", "civ_bonuses.jsonl")


def test_two_closed_neighbour_bonuses_merge_without_a_conflict(tmp_path):
    rows = [json.loads(s) for s in open(os.path.join(ROOT, FILE))]
    i = next(i for i in range(len(rows) - 1) if rows[i]["civ"] == rows[i + 1]["civ"])

    def closed(k):
        out = [dict(r) for r in rows]
        out[k] = {key: v for key, v in out[k].items() if key not in ("gap", "later")} | {"in": "COSTS"}
        return [json.dumps(r, ensure_ascii=False) + "\n" for r in out]
    d, path = str(tmp_path), tmp_path / FILE
    path.parent.mkdir(parents=True)
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "merge.jsonl.driver", f"{sys.executable} {TOOL} %O %A %B")
    (tmp_path / ".gitattributes").write_text(f"{FILE} merge=jsonl\n")
    base = open(os.path.join(ROOT, FILE)).read()
    for branch, text in (("main", base), ("ours", "".join(closed(i))), ("theirs", "".join(closed(i + 1)))):
        if branch != "main":
            git(d, "checkout", "-q", "-b", branch, "main")
        path.write_text(text)
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", branch)
    git(d, "checkout", "-q", "ours")
    assert git(d, "merge", "-q", "--no-edit", "theirs").returncode == 0
    both = [json.loads(s) for s in path.read_text().splitlines()]
    assert both[i]["in"] == both[i + 1]["in"] == "COSTS" and len(both) == len(rows)
    assert subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=d).returncode == 0
