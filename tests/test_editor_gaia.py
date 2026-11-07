"""The Gaia tab of the editor palette (#6036): relics, rocks, ruins and decor; a relic is placed as an object of Gaia."""
import contextlib
import io
import shutil

import editor
import export
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from test_editor_palette import eye_over, free_cells, state_of


def test_the_gaia_tab_has_drawn_objects_with_unit_ids_and_no_cliffs():
    tabs = dict(editor.tabs())
    gaia = tabs["gaia"]
    assert gaia and all(export.unit_id(n) is not None and editor.kind(n) == "O" for n in gaia)
    assert not any(n.startswith("CLIFF") for n in gaia)
    assert not set(gaia) & set(tabs["resources"])
    for part in ("RELIC", "ROCK", "RUIN", "FLOWER"):
        assert any(part in n for n in gaia), part


def test_a_relic_is_placed_as_gaia_and_saved(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    s.player = 2
    relic = "RELIC" if "RELIC" in dict(editor.tabs())["gaia"] else next(n for n in dict(editor.tabs())["gaia"] if "RELIC" in n)
    o = editor.place(s, "p", relic, *eye_over(s, free_cells(s, 1)[0]))
    assert o is not None and o["player"] == 0 and o["id"] == export.unit_id(relic)
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    assert (export.unit_id(relic), 0) in {(u.unit_const, p) for p in range(9) for u in scn.unit_manager.units[p]}
