"""A wall line in the editor (#6038): a right click at the start, one at the end, a segment on each tile."""
import contextlib
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import build  # noqa: E402
import editor  # noqa: E402
import export  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor_palette import eye_over, state_of  # noqa: E402

N = 4                                                                  # the tiles of a line: 0 to N-1


def free_square(s):
    """The tile (x, z) of the corner of N x N free tiles."""
    T = s.map.T
    for tz in range(1, s.map.n // T - N):
        for tx in range(1, s.map.n // T - N):
            if all(s.map.free(x, z) for x in range(tx * T, (tx + N) * T) for z in range(tz * T, (tz + N) * T)):
                return tx, tz
    raise AssertionError("no free square")


def line(s, name, a, b):
    T = s.map.T
    cell = lambda t: (t[0] * T + T // 2, t[1] * T + T // 2)        # noqa: E731
    assert editor.place(s, "p", name, *eye_over(s, cell(a))) is None and s.placed == []
    assert any(c.startswith("title p actionbar") for c in s.game.sent)
    assert editor.place(s, "p", name, *eye_over(s, cell(b))) is not None
    return {(int(o["tile"][0]), int(o["tile"][1])) for o in s.placed}


def test_a_straight_and_a_diagonal_line(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    name = build.WALLS[0]
    s = state_of(world)
    tx, tz = free_square(s)
    assert line(s, name, (tx, tz), (tx + N - 1, tz)) == {(tx + i, tz) for i in range(N)}
    s = state_of(world)
    got = line(s, name, (tx, tz), (tx + N - 1, tz + N - 1))
    assert got == set(build.wall_tiles(tx, tz, tx + N - 1, tz + N - 1)) and len(got) >= N
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    walls = [u for u in scn.unit_manager.units[1] if u.unit_const == export.unit_id(name)]
    assert len(walls) == len(got)
