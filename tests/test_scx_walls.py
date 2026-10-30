"""Units on a gate on a slope stand on its raised floor, and each unit above the ground has a debug line (#773:
Lights of Kurishima, Arrival in Juval Province)."""
import contextlib
import inspect
import io

import numpy as np
import pytest
from test_scx import build


@pytest.mark.parametrize("gate,diagonal,step", [(487, False, "y"), (659, True, "x"), (667, False, "y")])
def test_units_on_a_gate_on_a_slope_stand_on_its_floor(tmp_path, monkeypatch, gate, diagonal, step):
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
    elevation = np.zeros((24, 24), np.float32)
    elevation[(slice(12, None), slice(None)) if step == "x" else (slice(None), slice(11, None))] = 1   # a step under the gate
    path = build(tmp_path / "wall.scx", np.zeros((24, 24), np.int16), elevation, {1: (1, 1, (6.0, 6.0))}, objects=objects)
    monkeypatch.setenv("AOE2MC_DEBUG", "1")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([str(path), str(tmp_path / "W")])
    assert "units in a block (moved up): 0" in out.getvalue()
    assert "in block:" not in out.getvalue()


def test_each_moved_unit_has_a_debug_line(monkeypatch, capsys):
    import aoe2mc
    assert "MOVED[" not in inspect.getsource(aoe2mc.entity_chunk)          # all places count through moved()
    monkeypatch.setenv("AOE2MC_DEBUG", "1")
    col = np.full(aoe2mc.MAX_Y - aoe2mc.MIN_Y, aoe2mc.B("air"), np.uint16)
    col[64 - aoe2mc.MIN_Y] = aoe2mc.B("stone_bricks")
    aoe2mc.MOVED.clear()
    aoe2mc.moved("Villager", {"id": "minecraft:villager"}, 5, 64, 7, col)
    aoe2mc.moved("(on a bridge)", {"id": "minecraft:zombie"}, 5, 64, 7, col)
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["   in block: minecraft:villager 5 64 7 minecraft:stone_bricks minecraft:air",
                     "   on a bridge: minecraft:zombie 5 64 7 minecraft:stone_bricks minecraft:air"]
    assert aoe2mc.MOVED == {"Villager": 1, "(on a bridge)": 1}
    aoe2mc.MOVED.clear()
