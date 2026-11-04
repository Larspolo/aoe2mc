"""tools/dat_compare.py: the unit rows with no enum ID get their .dat ID from SAME_AS, or a warning line (#5733)."""
import json

import table

from tests.test_dat_compare_fixes import dat, unit
from tools import dat_compare as dc


def test_a_mod_villager_hp_gives_a_line(tmp_path):
    base, mod = dat([[], [unit(83, 25)]]), dat([[], [unit(83, 40)]])
    dc.write(base, mod, {}, {"units.jsonl": [{"name": "VILLAGER", "hp": 25}]}, str(tmp_path))
    assert [json.loads(s) for s in open(tmp_path / "units.jsonl")] == [{"name": "VILLAGER", "hp": 40}]


def test_a_row_with_no_id_prints_a_warning(tmp_path, capsys):
    d = dat([[], [unit(1)]])
    dc.write(d, d, {}, {"units.jsonl": [{"name": "NEW_ROW", "hp": 5}]}, str(tmp_path))
    assert "NEW_ROW: no .dat ID" in capsys.readouterr().out


def test_each_hp_row_of_the_data_has_an_id():
    units, _ = dc.names()
    lost = [r["name"] for r in table.load("units.jsonl") if "hp" in r and dc.SAME_AS.get(r["name"], units.get(r["name"])) is None]
    assert lost == []
