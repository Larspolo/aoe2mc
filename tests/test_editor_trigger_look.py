"""Select the objects, locations and areas of trigger fields by a look in the editor (#6091)."""
import contextlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from test_editor_palette import eye_over, free_cells, state_of  # noqa: E402
from test_editor_trigger_fields import add  # noqa: E402
from test_editor_trigger_types import click, opened  # noqa: E402
from test_editor_triggers_menu import saved, world_of  # noqa: E402
from test_export_triggers import by_ref  # noqa: E402

import aoe2mc  # noqa: E402


def look(s, part, *cells):
    """Click "Select by a look", then write `here` at each cell."""
    editor.fields_menu(s, "p", len(s.scenario.trigger_manager.triggers) - 1, len(editor.parts(
        s.scenario.trigger_manager.triggers[-1])) - 1)
    click(s, editor.LOOK)
    return [editor.here(s, "p", *eye_over(s, c)) for c in cells]


def start_cell(s):
    """A block cell inside a start object with a reference ID, and the ID."""
    for i, o in enumerate(s.data["objects"]):
        if o.get("ref") is not None and "tile" in o:
            r = editor.rect_of(s, o)[0]
            if editor.object_at(s, (r[0], r[2])) == o["ref"]:
                return (r[0], r[2]), o["ref"]


def test_a_look_at_a_start_and_a_placed_object_sets_the_object(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    s.command = lambda c: ""                                         # noqa: E731
    opened(s)
    cell, ref = start_cell(s)
    part = add(s, len(s.scenario.trigger_manager.triggers) - 1, "condition", "DESTROY_OBJECT")
    assert look(s, part, cell) == [True] and part.unit_object == ref
    placed = editor.place_at(s, 1, "ARCHER", free_cells(s, 1)[0])
    effect = add(s, len(s.scenario.trigger_manager.triggers) - 1, "effect", "KILL_OBJECT")
    at = tuple(placed["rect"][::2])
    assert look(s, effect, at, at) == [False, True] and effect.selected_object_ids == [placed["ref"]]
    scn = saved(s, tmp_path)
    t, refs = scn.trigger_manager.triggers[-1], by_ref(scn)
    assert t.conditions[-1].unit_object == ref and ref in refs
    assert t.effects[-1].selected_object_ids == [placed["ref"]] and refs[placed["ref"]][0] == placed["id"]


def test_two_looks_set_the_area_in_the_source_orientation(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    s.command = lambda c: ""                                         # noqa: E731
    s.data["turn"] = 1
    opened(s)
    part = add(s, len(s.scenario.trigger_manager.triggers) - 1, "condition", "OBJECTS_IN_AREA")
    a, b = free_cells(s, 2)
    assert look(s, part, a, b) == [False, True]
    T, n = s.map.T, s.data["map_size"]
    tiles = [tuple(int(v) for v in aoe2mc.turn_tile(c[0] // T + 0.5, c[1] // T + 0.5, n, 3)) for c in (a, b)]
    xs, ys = sorted(t[0] for t in tiles), sorted(t[1] for t in tiles)
    assert (part.area_x1, part.area_x2, part.area_y1, part.area_y2) == (*xs, *ys)


def test_a_removed_object_of_a_trigger_gives_the_export_line(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    s.command = lambda c: ""                                         # noqa: E731
    opened(s)
    cell, ref = start_cell(s)
    part = add(s, len(s.scenario.trigger_manager.triggers) - 1, "condition", "DESTROY_OBJECT")
    look(s, part, cell)
    editor.remove(s, "p", *eye_over(s, cell))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        editor.save(s.game, str(tmp_path / "o.aoe2scenario"), s)
    assert f"its object {ref} is not in the export" in out.getvalue()
