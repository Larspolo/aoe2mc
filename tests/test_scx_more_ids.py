"""The old object IDs that the check of the old campaigns (#606) still skipped (#772)."""
import contextlib
import io

import numpy as np

import aoe2mc
from test_scx import build

# Town center parts RTWC2X and RTWC1X, a palisade gate corner, a battering ram, FLAGX, shallows
OLD = [(1, 4.0, 4.0, 617), (1, 12.0, 4.0, 621), (1, 4.5, 12.5, 795), (1, 8.5, 12.5, 35), (0, 14.5, 14.5, 162),
       (0, 1.5, 14.5, 447)]


def scenario(tmp_path):
    return build(tmp_path / "old.scx", np.zeros((16, 16), np.int16), np.zeros((16, 16), np.float32),
                 {1: (1, 1, (6.0, 6.0))}, objects=OLD)


def test_old_ids_get_de_objects(tmp_path):
    size, terrain, _, names, _, objects, _ = aoe2mc.read_scx(str(scenario(tmp_path)))
    assert sorted((o["kind"], o["name"]) for o in objects) == [
        ("B", "PALISADE_WALL"), ("B", "TOWN_CENTER"), ("B", "TOWN_CENTER"), ("O", "INVISIBLE_OBJECT"), ("U", "BATTERING_RAM")]
    assert names[int(terrain[1, 14])] == "SHALLOWS" and names[int(terrain[2, 14])] != "SHALLOWS"   # 447: a terrain


def test_convert_skips_only_the_invisible_flag(tmp_path):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([str(scenario(tmp_path)), str(tmp_path / "W")])
    text = out.getvalue()
    assert "unknown" not in text and "invisible (skipped on purpose): 1" in text, text
    assert "units in a block (moved up): 0" in text, text
