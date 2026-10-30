"""Slow: the real sample maps in samples/ (#29) convert with valid states, biomes and entities, and no unit in a block.

Run with:  pytest -m slow
"""
import contextlib
import io
import os

import mcvalid
import pytest
import world_reader
from entities import entity_ids

import aoe2mc

SAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


@pytest.mark.slow
@pytest.mark.parametrize("name", ["gallery", "stress", "test_village", "unit_gallery"])
def test_sample_map_converts(name, tmp_path):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(os.path.join(SAMPLES, f"{name}.aoe2scenario"), str(tmp_path / "World"))
    log = out.getvalue()
    assert "units in a block (moved up): 0" in log, log
    w = world_reader.World(str(tmp_path / "World"))
    assert mcvalid.invalid_states(w.palette(), aoe2mc.VERSION_NAME) == {}
    biomes = {str(b) for c in w.chunks().values() for s in c["sections"] for b in s["biomes"]["palette"]}
    assert {b: mcvalid.biome_error(b, aoe2mc.VERSION_NAME) for b in biomes if mcvalid.biome_error(b, aoe2mc.VERSION_NAME)} == {}
    for e in w.entities(flat=False):
        for i in entity_ids(e):
            assert mcvalid.entity_error(i, aoe2mc.VERSION_NAME) is None, i
