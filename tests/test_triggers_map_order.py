"""The datapack text of each trigger type (`MAP` of tools/triggers.py) is one line per type in
`data/trigger_conditions.jsonl` and `data/trigger_effects.jsonl`: the merge driver `merge=jsonl` merges the lines by
name, and a merge without it (`merge=union`) keeps two lines of one name (2026-10-28)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import triggers  # noqa: E402


def test_each_type_has_one_line():
    for kind in ("condition", "effect"):
        with open(os.path.join(triggers.DATA, f"trigger_{kind}s.jsonl"), encoding="utf-8") as f:
            names = [json.loads(line)["name"] for line in f if line.strip()]
        assert len(names) == len(set(names)), f"two lines of one {kind}: take main's line and add yours again"
        assert all((kind, n) in triggers.MAP for n in names)


def test_the_data_files_merge_by_name():
    with open(os.path.join(triggers.ROOT, ".gitattributes")) as f:
        text = f.read()
    for kind in ("condition", "effect"):
        assert f"data/trigger_{kind}s.jsonl merge=jsonl" in text
