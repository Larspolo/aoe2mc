"""Cliffs in the editor (#6037): the tab, a placed cliff draws rock, saves with its ID and tile, converts to rock."""
import contextlib
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import export  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402
from test_editor_palette import eye_over, state_of  # noqa: E402
from test_editor_walls import free_square  # noqa: E402

import aoe2mc  # noqa: E402


def test_the_cliff_tab_has_unit_ids():
    names = dict(editor.tabs())["cliffs"]
    assert names and all(n.startswith("CLIFF") and export.unit_id(n) is not None for n in names)


def test_a_cliff_places_removes_saves_and_converts(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    T = s.map.T
    tx, tz = free_square(s)
    name = dict(editor.tabs())["cliffs"][0]
    cell = ((tx + 1) * T + T // 2, (tz + 1) * T + T // 2)            # the middle tile of 3 x 3 free tiles
    o = editor.place(s, "p", name, *eye_over(s, cell))
    assert o is not None and o["id"] == export.unit_id(name) and o["tile"] == [tx + 1.5, tz + 1.5]
    assert o["rect"] == [tx * T, (tx + 3) * T, tz * T, (tz + 3) * T]
    rock = ("stone", "andesite", "tuff", "cobblestone", "mossy_cobblestone")
    assert any(c.startswith("setblock ") and any(r in c for r in rock) or
               c.startswith("fill ") and any(r in c for r in rock) for c in s.game.sent)
    assert editor.remove(s, "p", *eye_over(s, cell)) is not None and s.placed == []
    o = editor.place(s, "p", name, *eye_over(s, cell))
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
        got = [u for u in scn.unit_manager.units[0] if u.unit_const == export.unit_id(name)]
        assert [(u.x, u.y) for u in got] == [(tx + 1.5, tz + 1.5)]
        aoe2mc.convert(out, str(tmp_path / "W2"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import world_reader
    w = world_reader.World(str(tmp_path / "W2"))
    x, z = int((tx + 1.5) * T), int((tz + 1.5) * T)
    assert any(b and any(r in b for r in rock) for b in (w.block(x, y, z) for y in range(-64, 200)))
