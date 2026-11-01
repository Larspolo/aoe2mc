"""run.py --data-mod FILE.dat writes the data mod folder of the mod into the world and uses it (#5356)."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import dat_compare  # noqa: E402
import run  # noqa: E402
import table  # noqa: E402
from test_start_on_join import FakeGame  # noqa: E402

LINE = {"name": "MOD_UNIT", "hp": 1}


def writer(calls):
    def main(argv):
        calls.append(argv)
        with open(os.path.join(argv[argv.index("--write") + 1], "units.jsonl"), "w") as f:
            f.write(json.dumps(LINE) + "\n")
        return 0
    return main


def test_a_dat_file_gives_the_cache_folder(tmp_path, monkeypatch):
    dat, calls = tmp_path / "mod.dat", []
    dat.write_bytes(b"")
    monkeypatch.setattr(dat_compare, "main", writer(calls))
    folder = run.data_mod_folder(str(tmp_path / "W"), str(dat))
    assert folder == str(tmp_path / "W" / "aoe2mc_data_mod") and calls == [[str(dat), "--write", folder]]
    assert json.loads(open(os.path.join(folder, "units.jsonl")).read()) == LINE
    assert run.data_mod_folder(str(tmp_path / "W"), str(dat)) == folder and len(calls) == 1   # the cache
    os.utime(dat, (os.path.getmtime(folder) + 10,) * 2)                                      # a newer .dat
    run.data_mod_folder(str(tmp_path / "W"), str(dat))
    assert len(calls) == 2


def test_main_plays_with_the_folder(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    dat = tmp_path / "mod.dat"
    dat.write_bytes(b"")
    monkeypatch.setattr(dat_compare, "main", writer([]))
    monkeypatch.setattr(table, "MOD", None)
    monkeypatch.delenv("AOE2MC_DATA_MOD", raising=False)
    monkeypatch.setattr(run, "Game", lambda *a, **k: FakeGame())
    monkeypatch.setattr(run, "play", lambda *a, **k: type("G", (), {"ended": None})())
    monkeypatch.setattr(run, "console", lambda game: None)
    monkeypatch.setattr(run, "ctrl_c", lambda: None)
    run.main([str(tmp_path), "--play", "--data-mod", str(dat)])
    assert table.MOD == os.environ["AOE2MC_DATA_MOD"] == str(tmp_path / "aoe2mc_data_mod")


def test_no_genieutils_gives_the_message_and_exit(tmp_path, monkeypatch, capsys):
    dat = tmp_path / "mod.dat"
    dat.write_bytes(b"")
    monkeypatch.setattr(dat_compare, "DEFAULT", str(dat))                # the base game .dat
    real = __import__
    monkeypatch.setattr("builtins.__import__", lambda n, *a, **k: (_ for _ in ()).throw(ImportError(n))
                        if n.startswith("genieutils") else real(n, *a, **k))
    with pytest.raises(SystemExit) as e:
        run.data_mod_folder(str(tmp_path / "W"), str(dat))
    assert "no genieutils-py: pip install genieutils-py" in capsys.readouterr().out
    assert "--write DIR" in str(e.value)
