"""The trigger and variable fields of trigger parts in the editor (#6112): a click selects the next trigger or
variable, the item shows its name, and the save has the ID."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import table  # noqa: E402
from test_editor_palette import state_of  # noqa: E402
from test_editor_trigger_fields import add, slot  # noqa: E402
from test_editor_trigger_types import click, opened  # noqa: E402
from test_editor_triggers_menu import saved, world_of  # noqa: E402


def test_activate_and_deactivate_select_the_next_trigger_by_name(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, t = opened(s)
    t.name = "Gate opens"
    active = add(s, at, "condition", "TRIGGER_ACTIVE")
    assert ("trigger_id", "trigger") in editor.fields("condition", active)
    shown = []
    s.menus_show = None
    for name in ("ACTIVATE_TRIGGER", "DEACTIVATE_TRIGGER"):
        e = add(s, at, "effect", name)
        assert ("trigger_id", "trigger") in editor.fields("effect", e)
        click(s, slot("effect", e, "trigger_id"))
        assert e.trigger_id == t.trigger_id
        shown.append(editor.ref_name(s.scenario.trigger_manager, "trigger", e.trigger_id))
    assert all("Gate opens" in n for n in shown)
    effects = saved(s, tmp_path).trigger_manager.triggers[at].effects
    assert [e.trigger_id for e in effects[-2:]] == [t.trigger_id] * 2


def variable_types(tiny_world, tmp_path):
    """The (kind, name) of the types with a variable field (a scratch world: a save of all types fails)."""
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    return [(kind, r["name"]) for kind in editor.KINDS
            for r in table.load(os.path.join(editor.CONVERTER_DATA, editor.KINDS[kind]))
            if any(f == "variable" for _, f in editor.fields(kind, add(s, at, kind, r["name"])))]


def test_each_variable_field_selects_the_next_variable(tiny_world, tmp_path):
    types = variable_types(tiny_world, tmp_path / "scratch")
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    tm = s.scenario.trigger_manager
    tm.add_variable("Gold left", 3)
    want = {}
    for kind, name in types:
        part = add(s, at, kind, name)
        for a in ("variable", "variable2"):
            if (a, "variable") not in editor.fields(kind, part):
                continue
            setattr(part, a, 2)
            editor.fields_menu(s, "p", at, len(editor.parts(tm.triggers[at])) - 1)
            click(s, slot(kind, part, a))
            assert getattr(part, a) == 3, (name, a)
            want[(len(editor.parts(tm.triggers[at])) - 1, a)] = 3
    assert {a for _, a in want} == {"variable", "variable2"} and len(types) > 5
    assert "Gold left" in editor.ref_name(tm, "variable", 3) and editor.ref_name(tm, "variable", 7) == "7: Variable 7"
    t = saved(s, tmp_path).trigger_manager.triggers[at]
    for (i, a), v in want.items():
        assert getattr(editor.parts(t)[i][1], a) == v
