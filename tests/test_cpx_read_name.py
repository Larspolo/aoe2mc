"""The conversion of an old campaign prints the file name of each scenario, not of a temporary file (#578)."""
import contextlib
import io

from test_campaign import cpx, scx_bytes

import aoe2mc


def test_cpx_prints_the_scenario_file_name(tmp_path):
    a = scx_bytes(tmp_path, "a.scx", {1: (1, 0, (8, 8))})
    c = cpx(tmp_path / "old.cpx", [("Lights of Kurishima.scx", a)])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([str(c), str(tmp_path / "out")])
    assert "Read Lights of Kurishima.scx:" in out.getvalue() and "Read s.scx" not in out.getvalue()
