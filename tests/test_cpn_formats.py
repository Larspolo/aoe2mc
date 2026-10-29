"""An old campaign converts each scenario of a format that scx.py reads, by its format, not its file name (#3863)."""
import contextlib
import io

import numpy as np
import pytest

import aoe2mc
from test_campaign import cpx, scx_bytes
from test_scn import build


def test_cpn_converts_118_and_121_and_gives_the_steps_for_the_rest(tmp_path):
    t, e = np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32)
    old = build(tmp_path / "a.scn", b"1.18", t, e, {1: (1, 0, (8, 8))}).read_bytes()
    new = scx_bytes(tmp_path, "b.scx", {1: (2, 1, (4, 4))})
    assert (old[:4], new[:4]) == (b"1.18", b"1.21")
    c = cpx(tmp_path / "old.cpn", [("Eins.scn", old), ("Zwei", new), ("Drei.scx", b"1.10" + bytes(9))])
    out = io.StringIO()
    with pytest.raises(SystemExit) as x, contextlib.redirect_stdout(out):
        aoe2mc.main([str(c), str(tmp_path / "out")])
    assert "  3 Drei.scx" in str(x.value.code) and "Eins" not in str(x.value.code)
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1 Eins", "2 Zwei", "3 Drei.scx", "campaign.json"]
    assert (tmp_path / "out" / "1 Eins" / "level.dat").exists() and (tmp_path / "out" / "2 Zwei" / "level.dat").exists()


def test_help_and_docstring_name_the_formats():
    assert "1.18 to 1.20" in aoe2mc.__doc__ and "HD 1.22 to 1.26" in aoe2mc.__doc__
    h = io.StringIO()
    with pytest.raises(SystemExit), contextlib.redirect_stdout(h):
        aoe2mc.main(["--help"])
    assert "HD 1.22 to 1.26" in " ".join(h.getvalue().split())
