"""The Resources tab of the editor palette has the trees and the berry bushes (#6016): they draw blocks and go into
the scenario of Gaia."""
import contextlib
import io
import shutil

import editor
import export
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from test_editor_palette import eye_over, free_cells, state_of


def resources():
    return dict(editor.tabs())["resources"]


def test_the_resources_tab_has_a_tree_and_a_bush_with_unit_ids():
    res = resources()
    assert any("TREE" in n for n in res) and "FORAGE_BUSH" in res
    assert all(export.unit_id(n) is not None for n in res)


def test_a_placed_tree_and_bush_draw_blocks_and_go_into_the_scenario(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    tree = next(n for n in resources() if "TREE" in n)
    for name, cell in zip((tree, "FORAGE_BUSH"), free_cells(s, 2)):
        before = len(s.game.sent)
        got = editor.place(s, "p", name, *eye_over(s, cell))
        assert got is not None and got["player"] == 0, name
        assert any(c.startswith(("setblock", "fill")) for c in s.game.sent[before:]), name
    tiles = [p["tile"] for p in s.placed]
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    got = {(u.unit_const, int(u.x), int(u.y)) for u in scn.unit_manager.units[0]}
    for name, (x, y) in zip((tree, "FORAGE_BUSH"), tiles):
        assert (export.unit_id(name), int(x), int(y)) in got, name
