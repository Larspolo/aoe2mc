"""The unit values of the game program are one JSON line per unit in game/data/units.jsonl (#1912)."""
import json
import os
import sys

import pytest

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import combat  # noqa: E402
import table  # noqa: E402

PATH = os.path.join(table.DIR, "units.jsonl")


def test_each_line_has_the_stats_fields():
    for line in open(PATH, encoding="utf-8"):
        row = json.loads(line)
        assert {"name", *combat.Stats._fields} - {"blast", "passes", "pass_part"} <= set(row), row["name"]   # other keys: test_data_files.py (#2164)
        assert isinstance(row["bonus"], dict) and isinstance(row["classes"], list), row["name"]
        assert all(isinstance(row[f], (int, float)) for f in ("hp", "attack", "melee", "pierce", "range", "reload"))


def test_stats_come_from_the_file():
    rows = table.load("units.jsonl")
    assert list(combat.STATS) == [r["name"] for r in rows]
    assert all(isinstance(s.classes, tuple) for s in combat.STATS.values())


def test_a_name_in_two_lines_stops_the_load(tmp_path):
    line = open(PATH, encoding="utf-8").readline()
    p = tmp_path / "units.jsonl"
    p.write_text(line + line, encoding="utf-8")
    with pytest.raises(ValueError, match="MILITIA"):
        table.load(str(p))
