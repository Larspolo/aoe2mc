"""The building values and the line of sight of the game program are lines in the data files (#1913):
game/data/buildings.jsonl (one line per building) and the key "sight" in game/data/units.jsonl."""
import json
import os
import re
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import combat  # noqa: E402
import table  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_each_building_line_has_the_stats_fields_or_only_a_sight():
    for line in open(os.path.join(table.DIR, "buildings.jsonl"), encoding="utf-8"):
        row = json.loads(line)
        # only the required keys: an optional key is no line here (#2164), test_data_files.py checks its type
        shapes = [k for k in ({"name", *combat.Stats._fields} - {"blast", "passes", "pass_part"}, {"name", "hp_ages", "melee", "pierce"}) if k <= set(row)]
        assert shapes or not set(row) & {*combat.Stats._fields, "hp_ages"}, row["name"]
        assert "sight" in row or shapes, row["name"]


def test_the_code_adds_the_classes_of_the_buildings():
    assert all((combat.STANDARD in s.classes) == (n != "WONDER") for n, s in combat.BUILDINGS.items())
    assert all(combat.STONE in s.classes for n, s in combat.BUILDINGS.items() if n.endswith("_TOWER") or n == "KEEP")
    only = {r["name"] for r in table.load("buildings.jsonl") if not set(r) & {*combat.Stats._fields, "hp_ages"}}
    assert not only & set(combat.BUILDINGS)                          # a line with only a sight has no target


def test_each_sight_belongs_to_a_line_of_a_unit_or_a_building():
    names = {r["name"] for r in table.load("units.jsonl") + table.load("buildings.jsonl")}
    assert set(combat.SIGHT) <= names


def test_combat_py_has_no_literal_of_the_tables():
    src = open(os.path.join(ROOT, "game", "combat.py"), encoding="utf-8").read()
    assert not re.search(r"^(BUILDINGS|SIGHT) = \{$", src, re.M)
