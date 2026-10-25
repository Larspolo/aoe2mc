"""Slow: the test maps of tools/scenarios.py convert without errors, with valid states and no unit in a block.

Run with:  pytest -m slow
"""
import contextlib
import io

import pytest

import aoe2mc
import mcvalid
import scenarios
import world_reader
from conftest import entity_ids


@pytest.mark.slow
@pytest.mark.parametrize("kind", ["stress", "village", "units", "buildings", "river_town", "four_civs"])
def test_scenario_converts(kind, tmp_path):
    make = scenarios.MAKERS[kind]
    src = str(tmp_path / f"{kind}.aoe2scenario")
    make(src, n_civs=2) if kind == "buildings" else make(src)     # 2 civilizations keep the test short
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "World"))
    log = out.getvalue()
    assert "units in a block (moved up): 0" in log, log
    if kind == "stress":
        assert "units on bridges: 3" in log
    w = world_reader.World(str(tmp_path / "World"))
    assert mcvalid.invalid_states(w.palette(), aoe2mc.VERSION_NAME) == {}
    for e in w.entities(flat=False):
        for i in entity_ids(e):
            assert mcvalid.entity_error(i, aoe2mc.VERSION_NAME) is None, i
