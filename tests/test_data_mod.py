"""The data mod (#5353): a folder whose lines change the lines of game/data of the same name (table.MOD, run.py
--data-mod). The names and values come from the data file, so that a balance change does not break these tests."""
import json
import os

import pytest
import run
import table

FILE = "units.jsonl"
BASE = table.read(os.path.join(table.DIR, FILE))
ROW = BASE[0]
KEY = "hp"
OTHER = next(k for k in ROW if k not in ("name", KEY))


def mod(tmp_path, lines):
    (tmp_path / FILE).write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="utf-8")
    return str(tmp_path)


def test_mod_line_changes_its_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(table, "MOD", mod(tmp_path, [{"name": ROW["name"], KEY: ROW[KEY] + 1}]))
    rows = table.load(FILE, "aoe2")
    assert [r["name"] for r in rows] == [r["name"] for r in BASE]
    assert rows[0] == ROW | {KEY: ROW[KEY] + 1}
    assert rows[0][OTHER] == ROW[OTHER]
    assert rows[1:] == BASE[1:]


def test_mod_line_of_unknown_name_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(table, "MOD", mod(tmp_path, [{"name": "NOT_A_UNIT", KEY: 1}]))
    assert table.load(FILE, "aoe2") == BASE


def test_no_mod_gives_the_data(monkeypatch):
    monkeypatch.setattr(table, "MOD", None)
    assert table.load(FILE, "aoe2") == BASE


def test_missing_mod_folder_stops(tmp_path):
    with pytest.raises(SystemExit, match="not a folder"):
        run.main(["WORLD", "--data-mod", str(tmp_path / "missing")])
