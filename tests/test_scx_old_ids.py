"""Old object IDs of .scx scenarios that DE keeps only in its data file get a DE object of the same look (#576)."""
import contextlib
import io

import numpy as np
from test_scx import build

import aoe2mc

OLD = [(0, 3.5, 3.5, 248), (0, 6.5, 3.5, 262), (0, 9.5, 3.5, 415), (0, 11.5, 3.5, 737), (1, 6.0, 10.0, 10),
       (0, 12.5, 12.5, 162)]


def scenario(tmp_path):
    return build(tmp_path / "old.scx", np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                 {1: (1, 1, (6.0, 6.0))}, objects=OLD)


def test_convert_places_the_old_objects(tmp_path):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([str(scenario(tmp_path)), str(tmp_path / "W")])
    text = out.getvalue()
    assert "unknown to the parser" not in text and "invisible (skipped on purpose): 1" in text, text   # FLAGX (#772)
    assert "units in a block (moved up): 0" in text
