"""tools/dat_compare.py --write: the unit values of a data mod .dat as data mod lines (#5354, epic #5352)."""
import json
from types import SimpleNamespace as NS

from tests.test_dat_compare import dat, unit
from tools import dat_compare as dc

FEUDAL_ATTACK = {101: [(4, -1, 6, dc.ATTACK, 4 * 256 + 2)]}      # Feudal Age: class 6, melee attack +2


def lines(tmp_path, base, mod, row, f="units.jsonl"):
    n = dc.write(base, mod, {"U": 1}, {f: [row]}, str(tmp_path))
    rows = [json.loads(s) for s in open(tmp_path / f, encoding="utf-8")]
    assert n == len(rows)
    return rows


def test_a_changed_value_gives_a_line_with_only_that_key(tmp_path):
    base, mod = dat([[], [unit(1, 40)]]), dat([[], [unit(1, 45)]])
    assert lines(tmp_path, base, mod, {"name": "U", "hp": 40, "attack": 4}) == [{"name": "U", "hp": 45}]


def test_the_value_of_the_age_of_the_data_line(tmp_path):
    base = dat([[], [unit(1, 40, attack=4)]], FEUDAL_ATTACK)
    mod = dat([[], [unit(1, 40, attack=5)]], FEUDAL_ATTACK)
    row = {"name": "U", "hp": 40, "attack": 6}                       # the Feudal Age value of the base .dat
    assert lines(tmp_path, base, mod, row) == [{"name": "U", "attack": 7}]


def test_a_changed_age_effect_changes_the_value(tmp_path):
    base = dat([[], [unit(1, 40)]], FEUDAL_ATTACK)
    mod = dat([[], [unit(1, 40)]], {101: [(4, -1, 6, dc.ATTACK, 4 * 256 + 3)]})
    assert lines(tmp_path, base, mod, {"name": "U", "attack": 6}) == [{"name": "U", "attack": 7}]


def test_no_change_gives_no_line_and_the_file_has_no_old_line(tmp_path):
    (tmp_path / "units.jsonl").write_text('{"name": "U", "hp": 1}\n', encoding="utf-8")
    d = dat([[], [unit(1, 40)]])
    assert lines(tmp_path, d, d, {"name": "U", "hp": 40, "attack": 4, "melee": 0, "pierce": 1, "bonus": {}}) == []


def test_an_own_value_of_aoe2mc_stays(tmp_path):
    base, mod = dat([[], [unit(1, 40)]]), dat([[], [unit(1, 45)]])
    assert lines(tmp_path, base, mod, {"name": "U", "hp": 99}) == []        # the base .dat has no 99


def test_an_accepted_key_stays(tmp_path, monkeypatch):
    monkeypatch.setitem(dc.ACCEPTED, ("U", "hp"), "test")
    base, mod = dat([[], [unit(1, 40)]]), dat([[], [unit(1, 45)]])
    assert lines(tmp_path, base, mod, {"name": "U", "hp": 40}) == []


def test_a_bonus_keeps_the_negative_bonus_of_the_data(tmp_path):
    def with_bonus(amount):
        u = unit(1, 40)
        u.type_50.attacks.append(NS(class_=8, amount=amount))           # class 8: cavalry
        return u
    base, mod = dat([[], [with_bonus(4)]]), dat([[], [with_bonus(6)]])
    row = {"name": "U", "bonus": {"cavalry": 4, "condottiero": -10}}
    assert lines(tmp_path, base, mod, row) == [{"name": "U", "bonus": {"condottiero": -10, "cavalry": 6}}]


def test_the_walk_speed_of_a_replay_line(tmp_path):
    base, mod = dat([[], [unit(1, 40)]]), dat([[], [unit(1, 40)]])
    mod.civs[1].units[1].speed = 1.1
    row = {"name": "U", "walk": 0.9, "hp": 7}                        # replay.jsonl: only the walk speed counts
    assert lines(tmp_path, base, mod, row, "replay.jsonl") == [{"name": "U", "walk": 1.1}]


def test_write_needs_the_base_dat(tmp_path):
    mod = tmp_path / "mod.dat"
    mod.write_bytes(b"")
    assert dc.main([str(mod), "--write", str(tmp_path / "out"), "--base", str(tmp_path / "none.dat")]) == 2
    assert not (tmp_path / "out").exists()
