"""The palette of the editor (#6013): the tabs, a pick and a right click place a building, a unit and a resource."""
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
from test_editor import FakeGame  # noqa: E402


def state_of(world):
    s = editor.State(FakeGame(world))
    s.menus = {}
    return s


def eye_over(s, cell):
    """An eye 3 blocks over the ground of cell, that looks straight down."""
    return (cell[0] + 0.5, s.map.y(*cell) + 3, cell[1] + 0.5), (0.0, -1.0, 0.0)


def free_cells(s, k):
    """k cells in free tiles far apart (the middle of each tile)."""
    T, out = s.map.T, []
    for tz in range(1, s.map.n // T - 1, 3):
        for tx in range(1, s.map.n // T - 1, 3):
            if all(s.map.free(x, z) for x in range(tx * T - T, tx * T + 2 * T) for z in range(tz * T - T, tz * T + 2 * T)):
                out.append((tx * T + T // 2, tz * T + T // 2))
                if len(out) == k:
                    return out
    return out


def test_the_tabs_come_from_the_data_and_have_unit_ids():
    tabs = dict(editor.tabs())
    assert list(tabs) == ["units", "buildings", "resources", "gaia"]
    assert all(tabs[t] and all(export.unit_id(n) is not None for n in tabs[t]) for t in tabs)


def test_a_tab_click_and_a_right_click_place(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    cell = free_cells(s, 1)[0]
    s.look = lambda p: eye_over(s, cell)
    editor.open_menu(s, "p")
    s.menus["p"]("p", editor.PAGE + 1, False)                       # the tab Buildings
    name = dict(editor.tabs())["buildings"][0]
    s.menus["p"]("p", 0, False, right=True)
    assert s.picked["p"] == name and len(s.placed) == 1 and s.placed[0]["id"] == export.unit_id(name)


def test_placed_objects_go_into_the_scenario_and_not_on_each_other(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    tabs = dict(editor.tabs())
    house = "HOUSE" if "HOUSE" in tabs["buildings"] else tabs["buildings"][0]
    unit = next(n for n in tabs["units"] if editor.kind(n) == "U")
    mine = next(n for n in tabs["resources"] if editor.kind(n) == "O")
    cells = free_cells(s, 3)
    for name, cell in zip((house, unit, mine), cells):
        assert editor.place(s, "p", name, *eye_over(s, cell)) is not None, name
    assert editor.place(s, "p", unit, *eye_over(s, cells[0])) is None      # on the house
    assert any(c.startswith("summon ") for c in s.game.sent)
    out = str(tmp_path / "out.aoe2scenario")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    got = {(u.unit_const, p) for p in range(9) for u in scn.unit_manager.units[p]}
    assert {(export.unit_id(house), 1), (export.unit_id(unit), 1), (export.unit_id(mine), 0)} <= got
