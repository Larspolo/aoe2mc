"""Wrong command-line options give an argparse error at the start, not a traceback later."""
import contextlib
import io

import pytest
import scenarios

import aoe2mc


def error(tmp_path, *opts, src="in.aoe2scenario"):
    err = io.StringIO()
    with pytest.raises(SystemExit) as e, contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([src, str(tmp_path / "W"), *opts])
    assert e.value.code == 2
    assert not (tmp_path / "W").exists()
    return err.getvalue()


@pytest.mark.parametrize("opts, msg", [
    (["--tile-size", "0"], "0 is not in the range 1-16"),
    (["--tile-size", "-2"], "-2 is not in the range 1-16"),
    (["--tile-size", "17"], "17 is not in the range 1-16"),
    (["--tile-size", "x"], "'x' is not an integer"),
    (["--level-height", "-1"], "-1 is not in the range 1-16"),
    (["--level-height", "0"], "0 is not in the range 1-16"),
    (["--player-architecture", "6=foo"], "unknown set 'foo' (choose from"),
    (["--player-architecture", "6"], "'6' is not P=SET"),
    (["--player-architecture", "x=western"], "'x=western' is not P=SET"),
])
def test_bad_option(tmp_path, opts, msg):
    assert msg in error(tmp_path, *opts)


def test_set_names_in_message(tmp_path):
    msg = error(tmp_path, "--player-architecture", "6=foo")
    assert all(a in msg for a in aoe2mc.buildings.ARCH)


def test_player_not_in_scenario(tmp_path):
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    msg = error(tmp_path, "--player-architecture", "9=western", src=src)
    assert "player 9 is not in the scenario (players: 0, 1, 2, 3, 4, 5, 6, 7, 8)" in msg


def test_good_options():
    assert aoe2mc.int_range(1, 16)("16") == 16
    assert aoe2mc.player_arch_spec("6=western") == (6, "western")


def test_verbose_prints_the_time_of_each_phase(tmp_path):
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([src, str(tmp_path / "W"), "--verbose"])
    line = next(ln for ln in out.getvalue().splitlines() if ln.startswith("  time: "))
    assert [p.split()[0] for p in line[8:].split(", ")] == ["read", "columns", "objects", "units", "chunks", "write"]
