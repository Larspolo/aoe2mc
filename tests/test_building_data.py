"""The building values and the line of sight of the game program are lines in the data files (#1913):
game/data/buildings.jsonl (one line per building) and the key "sight" in game/data/units.jsonl."""
import json
import os
import re
import subprocess
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import combat  # noqa: E402
import table  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_each_building_line_has_the_stats_fields_or_only_a_sight():
    for line in open(os.path.join(table.DIR, "buildings.jsonl"), encoding="utf-8"):
        row = json.loads(line)
        keys = set(row) - {"note", "sight", "stone"}                     # "stone": the class Stone Defense (#1873)
        assert keys in ({"name"}, {"name", *combat.Stats._fields}), row["name"]
        assert "sight" in row or keys != {"name"}, row["name"]


def test_buildings_and_sight_have_the_values_of_before():
    assert len(combat.BUILDINGS) >= 23 and len(combat.SIGHT) >= 154   # new units and buildings add lines (#1953, #1874)
    assert combat.BUILDINGS["DOCK"] == combat.Stats(1800, 3, 0, 7, 6, 2.0, {combat.CAM: 1, combat.SHIP: 3},   # (#1949)
                                                     ("building", combat.STANDARD))
    assert combat.BUILDINGS["KEEP"].classes == ("building", combat.STANDARD, combat.STONE)
    assert combat.BUILDINGS["WONDER"].classes == ("building",)
    assert list(combat.BUILDINGS)[:2] == ["HOUSE", "BARRACKS"]
    assert {n: combat.SIGHT[n] for n in ("HOUSE", "CAMEL_RIDER", "OUTPOST", "DONJON", "FORTIFIED_TOWER")} == \
        {"HOUSE": 2, "CAMEL_RIDER": 5, "OUTPOST": 4, "DONJON": 10, "FORTIFIED_TOWER": 14}
    assert "OUTPOST" not in combat.BUILDINGS                          # a line with only a sight has no target


def test_each_sight_belongs_to_a_line_of_a_unit_or_a_building():
    names = {r["name"] for r in table.load("units.jsonl") + table.load("buildings.jsonl")}
    assert set(combat.SIGHT) <= names


def test_the_file_merges_by_name():
    out = subprocess.run(["git", "check-attr", "merge", "game/data/buildings.jsonl"], cwd=ROOT, capture_output=True,
                         text=True).stdout
    assert out.strip().endswith("merge: jsonl")     # tools/merge_jsonl.py (#2004)


def test_combat_py_has_no_literal_of_the_tables():
    src = open(os.path.join(ROOT, "game", "combat.py"), encoding="utf-8").read()
    assert not re.search(r"^(BUILDINGS|SIGHT) = \{$", src, re.M)
