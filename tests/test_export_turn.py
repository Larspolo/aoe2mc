"""game/export.py: a world converted with --orientation exports to the orientation of its source (#5674)."""
import contextlib
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import export  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def units(scn):
    return sorted((u.unit_const, int(u.player), float(u.x), float(u.y)) for p in scn.unit_manager.units for u in p)


@pytest.fixture(scope="module")
def turned(tmp_path_factory):
    """The tiny scenario converted with a turn (orientation se): (source path, world path)."""
    d = tmp_path_factory.mktemp("turn")
    src = scenarios.tiny(str(d / "tiny.aoe2scenario"))
    world = str(d / "TurnWorld")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world, orientation="se")
    return src, world


def test_turned_world_exports_terrain_and_elevation_of_source(turned, tmp_path):
    src, world = turned
    back = read(export.export(world, str(tmp_path / "back.aoe2scenario")))
    ref = read(src)
    want = {(t.x, t.y): (t.terrain_id, t.elevation) for t in ref.map_manager.terrain}
    got = {(t.x, t.y): (t.terrain_id, t.elevation) for t in back.map_manager.terrain}
    assert got == want


def test_turned_world_exports_object_places_of_source(turned, tmp_path):
    src, world = turned
    back = units(read(export.export(world, str(tmp_path / "back.aoe2scenario"))))
    ref = units(read(src))
    assert [(i, p) for i, p, _, _ in back] == [(i, p) for i, p, _, _ in ref]
    for (_, _, x, y), (_, _, rx, ry) in zip(back, ref):
        assert abs(x - rx) <= 0.5 and abs(y - ry) <= 0.5
