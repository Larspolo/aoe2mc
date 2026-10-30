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
from entities import entity_ids


@pytest.mark.slow
@pytest.mark.parametrize("kind", ["stress", "village", "units", "buildings", "river_town", "four_civs", "battle"])
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


@pytest.mark.slow
def test_raised_river_objects_stand_at_its_surface(tmp_path):
    """The river of the `river` map lies at elevation 2: docks, bridges, boats and fish use its surface (#155)."""
    src = scenarios.river(str(tmp_path / "river.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "World"))
    assert "units in a block (moved up): 0" in out.getvalue()
    w = world_reader.World(str(tmp_path / "World"))
    name = lambda x, y, z: w.block(x, y, z).split("[")[0].split(":")[-1]
    top = lambda x, z, kind: max(y for y in range(aoe2mc.WATER_Y - 10, aoe2mc.WATER_Y + 20) if kind in name(x, y, z))
    surface = top(58, 50, "water")                                    # tile (14, 12), the middle of the river
    assert surface == aoe2mc.WATER_Y + 2 * 3 and top(58, 30, "dirt") == surface + 1     # 1 block below the land
    for x, z, kind in ((26, 42, "planks"), (98, 52, "stone_bricks")):                  # the dock and the bridge deck
        assert surface < top(x, z, kind) <= surface + 2, (x, z, kind)
    ids = sorted(str(e["id"]) for e in w.entities())
    assert ids.count("minecraft:cod") == 1 and sum(i.endswith("boat") for i in ids) == 2, ids
    for e in w.entities():
        x, y, z = (float(v) for v in e["Pos"])
        if str(e["id"]).endswith("boat"):
            assert y == top(int(x), int(z), "water") + 0.5, e["id"]
        elif e["id"] == "minecraft:cod":
            assert name(int(x), int(y), int(z)) == "water" and y <= top(int(x), int(z), "water") + 1
