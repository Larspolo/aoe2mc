"""A negative --seed stops with a usage error that names the option (#3038)."""

import pytest

import aoe2mc


def test_a_negative_seed_is_a_usage_error(tmp_path, capsys):
    out = tmp_path / "OUT"
    with pytest.raises(SystemExit) as stop:
        aoe2mc.main(["--random-map", "arabia", str(out), "--seed", "-1"])
    assert stop.value.code == 2
    assert "--seed" in capsys.readouterr().err
    assert not (out / "level.dat").exists()


def test_seed_zero_is_accepted(tmp_path):
    out = tmp_path / "OUT"
    aoe2mc.main(["--random-map", "arabia", str(out), "--seed", "0"])
    assert (out / "level.dat").exists()
