"""The remove of the editor (#6002): a removed start object and a removed placed object are not in the scenario, and
the tiles of a removed building are free for a new object."""
import contextlib
import io
import shutil

import build
import editor
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from test_editor_palette import eye_over, free_cells, state_of


def units_of(s, out):
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(s.game, out, s)
        scn = AoE2DEScenario.from_file(out)
    return sorted((u.unit_const, p) for p in range(9) for u in scn.unit_manager.units[p])


def start_building(s):
    i, o = next((i, o) for i, o in enumerate(s.data["objects"]) if o["kind"] == "building" and "footprint" in o)
    x0, z0, x1, z1 = o["footprint"]
    return i, o, ((x0 + x1) // 2, (z0 + z1) // 2)


def test_removed_objects_are_not_in_the_scenario(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    before = units_of(s, str(tmp_path / "a.aoe2scenario"))
    i, o, cell = start_building(s)
    assert editor.remove(s, "p", *eye_over(s, cell)) is not None
    assert i in s.removed and any(c.startswith("fill ") and c.endswith(" air") for c in s.game.sent)
    unit = next(n for n in dict(editor.tabs())["units"] if editor.kind(n) == "U")
    far = free_cells(s, 1)[0]
    assert editor.place(s, "p", unit, *eye_over(s, far)) is not None
    assert editor.remove(s, "p", *eye_over(s, far)) is not None and s.placed == []
    got = units_of(s, str(tmp_path / "b.aoe2scenario"))
    expect = list(before)
    expect.remove((o["id"], o["player"]))
    assert got == expect


def test_the_tiles_of_a_removed_building_are_free(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    _, o, cell = start_building(s)
    x0, z0, x1, z1 = o["footprint"]
    assert not build.free(s, (x0, x1, z0, z1))
    editor.remove(s, "p", *eye_over(s, cell))
    assert build.free(s, (x0, x1, z0, z1))
    unit = next(n for n in dict(editor.tabs())["units"] if editor.kind(n) == "U")
    assert editor.place(s, "p", unit, *eye_over(s, cell)) is not None


def test_nothing_to_remove_on_free_ground(tiny_world, tmp_path):
    world = str(tmp_path / "w")
    shutil.copytree(tiny_world[0], world)
    s = state_of(world)
    assert editor.remove(s, "p", *eye_over(s, free_cells(s, 1)[0])) is None and not s.removed
