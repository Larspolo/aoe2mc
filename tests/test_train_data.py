"""The menu items of the game program are one JSON line each in game/data/train.jsonl, and tools/merge_jsonl.py merges
two new lines (#1702, #2004)."""
import json

import pytest

import merge_jsonl
from game import train

KEYS = {"name", "building", "slot", "item", "label", "cost", "time", "help"}


def test_each_line_is_one_item_with_its_fields():
    lines = open(train.DATA, encoding="utf-8").read().splitlines()
    rows = [json.loads(s) for s in lines]
    assert len(rows) == len(train.ITEMS) == len(train.COSTS) == len(train.HELP)
    for r in rows:
        assert KEYS <= set(r), r["name"]                  # other keys: test_data_files.py checks their type (#2164)
        assert r.get("civ") is None or r["building"] is None and r["civ"] in {c["name"] for c in train.civs.ROWS}, r["name"]   # (#2021)
        assert r["building"] is None or r["building"] in train.TRAINS
        assert r.get("after") is None or r["after"] in train.ITEMS


def test_two_lines_of_one_name_stop_the_load(tmp_path):
    line = open(train.DATA, encoding="utf-8").readline()
    p = tmp_path / "train.jsonl"
    p.write_text(line + line.replace('"time": 25', '"time": 30'), encoding="utf-8")
    with pytest.raises(ValueError, match=json.loads(line)["name"]):
        train.load(str(p))


def test_two_new_items_of_one_building_merge_without_a_conflict(tmp_path):
    lines = open(train.DATA, encoding="utf-8").read().splitlines(keepends=True)
    end = max(i for i, s in enumerate(lines) if json.loads(s)["building"] == "BARRACKS") + 1
    new = [json.dumps({"name": n, "building": "BARRACKS", "slot": 30 + k, "item": "book", "label": n, "cost": {},
                       "time": 1, "help": n}) + "\n" for k, n in enumerate(("TEST_A", "TEST_B"))]
    base, ours, theirs = (tmp_path / n for n in ("base", "ours", "theirs"))
    base.write_text("".join(lines), encoding="utf-8")
    ours.write_text("".join(lines[:end] + new[:1] + lines[end:]), encoding="utf-8")
    theirs.write_text("".join(lines[:end] + new[1:] + lines[end:]), encoding="utf-8")
    assert merge_jsonl.main(["merge_jsonl.py", str(base), str(ours), str(theirs)]) == 0   # merge=jsonl (#2004)
    rows = train.load(str(ours))
    barracks = [r["name"] for r in rows if r["building"] == "BARRACKS"]
    assert barracks[-2:] == ["TEST_A", "TEST_B"] and len(rows) == len(lines) + 2
