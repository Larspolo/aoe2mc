"""A random map script with the ending .rms2 (the DE folder, #5363) reads as .rms: the same land, the same survey."""
import sys

import numpy as np
import rms_survey  # noqa: E402

import aoe2mc

SCRIPT = """/* Test */
<LAND_GENERATION>
base_terrain GRASS
create_land { terrain_type DIRT land_percent 10 land_position 50 50 base_size 5 }
"""


def test_rms2_reads_as_rms(tmp_path):
    rms, rms2 = tmp_path / "x.rms", tmp_path / "x.rms2"
    rms.write_text(SCRIPT)
    rms2.write_text(SCRIPT)
    a = aoe2mc.read_map(str(rms), 1, 2)
    b = aoe2mc.read_map(str(rms2), 1, 2)
    assert a[0] == b[0]
    assert np.array_equal(a[1], b[1])
    assert np.array_equal(a[2], b[2])


def test_survey_lists_rms2(tmp_path, capsys, monkeypatch):
    (tmp_path / "y.rms2").write_text(SCRIPT)
    monkeypatch.setattr(sys, "argv", ["rms_survey.py", str(tmp_path)])
    rms_survey.main()
    assert "| y |" in capsys.readouterr().out
