"""Units of an old scenario on a gate do not stand in its towers (#577: Kurishima, Juval)."""
import contextlib
import io

import numpy as np
import pytest
from test_scx import build


@pytest.mark.parametrize("gate,diagonal", [(487, False), (659, True), (667, False)])
def test_units_on_a_gate_stand_in_free_space(tmp_path, gate, diagonal):
    import aoe2mc
    if diagonal:
        objects = [(1, x + 0.5, x + 0.5, 117) for x in range(3, 20) if not 10 <= x <= 12] + [(1, 11.5, 11.5, gate)]
    else:
        objects = [(1, x + 0.5, 10.5, 117) for x in range(3, 20) if not 10 <= x <= 13] + [(1, 12.0, 10.5, gate)]
    rng = np.random.default_rng(1)
    for k in range(150):                                                     # villagers, knights, Joan on the wall line
        x = rng.uniform(3, 20)
        y = (x if diagonal else 10.5) + rng.uniform(-1.5, 1.5)
        objects.append((1, round(x * 4) / 4, round(y * 4) / 4, (83, 25, 430)[k % 3]))
    path = build(tmp_path / "wall.scx", np.zeros((24, 24), np.int16), np.zeros((24, 24), np.float32),
                 {1: (1, 1, (6.0, 6.0))}, objects=objects)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([str(path), str(tmp_path / "W")])
    assert "units in a block (moved up): 0" in out.getvalue()
