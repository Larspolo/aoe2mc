"""Each new group of the editor palette on a real server (#6039): a hero, a relic, a rock, a cliff and a wall line
placed in the editor save with their IDs, and aoe2mc.convert converts the save again."""
import contextlib
import io
import json
import os
import shutil
import sys

import pytest
from test_mc_check import mojang_reachable

import aoe2mc
from tools import scenarios

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
N = 4                                                                  # tiles of a free square: a cliff takes 3 x 3


def free_square(s):
    """The center tile (x, z) of N x N free tiles (the map of s after the earlier placements)."""
    T = s.map.T
    for tz in range(1, s.map.n // T - N):
        for tx in range(1, s.map.n // T - N):
            if all(s.map.free(x, z) for x in range(tx * T, (tx + N) * T) for z in range(tz * T, (tz + N) * T)):
                return tx + 1, tz + 1
    raise AssertionError("no free square")


@pytest.mark.mc
def test_each_new_palette_group_saves_and_converts(tmp_path):
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    import build
    import editor
    import export
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    from test_editor_palette import eye_over

    from game import run
    world, out = str(tmp_path / "W"), str(tmp_path / "OUT.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")), world)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    T = data["tile_size"]
    tabs = dict(editor.tabs())
    gaia = tabs["gaia"]
    want = [(tabs["heroes"][0], 1), (next(n for n in gaia if "RELIC" in n), 0),
            (next(n for n in gaia if "ROCK" in n), 0), (tabs["cliffs"][0], 0)]
    cell = lambda t: eye_over(s, (t[0] * T + T // 2, t[1] * T + T // 2))   # noqa: E731
    with run.Game(world) as game:
        game.forceload()
        s = editor.State(game, data)
        s.player = 1
        placed = []
        for name, p in want:                                           # a hero, a relic, a rock and a cliff
            o = editor.place(s, "p", name, *cell(free_square(s)))
            assert o is not None and o["player"] == p, name
            placed.append((export.unit_id(name), p))
        wall = build.WALLS[0]                                          # a wall line: two clicks
        tx, tz = free_square(s)
        assert editor.place(s, "p", wall, *cell((tx - 1, tz))) is None
        n = len(s.placed)
        assert editor.place(s, "p", wall, *cell((tx + 1, tz))) is not None
        segments = len(s.placed) - n
        assert segments == 3
        with contextlib.redirect_stdout(io.StringIO()):
            editor.save(game, out, s)
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(out)
    units = [(u.unit_const, p) for p in range(9) for u in scn.unit_manager.units[p]]
    for uid, p in placed:
        assert (uid, p) in units, (uid, p)
    start = sum(1 for o in data["objects"] if (o.get("id"), o.get("player")) == (export.unit_id(wall), 1))
    assert units.count((export.unit_id(wall), 1)) == start + segments
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W2"))                     # converts again with no error
    assert os.path.exists(tmp_path / "W2" / "level.dat")
    shutil.rmtree(tmp_path / "W2")
