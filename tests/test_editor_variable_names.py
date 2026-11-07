"""The name of a trigger variable in the editor (#6115): a shift click on a "Variable" item gives a book, and the book
sets the name of that variable; an empty book keeps the old name."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from test_editor_palette import state_of  # noqa: E402
from test_editor_trigger_fields import add, slot  # noqa: E402
from test_editor_trigger_name import book  # noqa: E402
from test_editor_trigger_types import click, opened  # noqa: E402
from test_editor_triggers_menu import saved, world_of  # noqa: E402


def variable_part(s, at, variable_id):
    """A CHANGE_VARIABLE effect of trigger at whose variable field is variable_id; returns (part, slot)."""
    part = add(s, at, "effect", "CHANGE_VARIABLE")
    part.variable = variable_id
    editor.fields_menu(s, "p", at, len(editor.parts(s.scenario.trigger_manager.triggers[at])) - 1)
    return part, slot("effect", part, "variable")


def test_a_shift_click_gives_a_book_and_the_book_names_the_variable(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    tm = s.scenario.trigger_manager
    tm.add_variable("Gold left", 3)
    part, sl = variable_part(s, at, 3)
    sent = book(s, "Wood left")
    click(s, sl, shift=True)
    assert any(c.startswith("give p minecraft:writable_book") and f"{at}." in c and "Variable 3" in c for c in sent)
    editor.read_books(s)
    assert [x.name for x in tm.variables if x.variable_id == 3] == ["Wood left"]
    assert part.variable == 3
    saved_tm = saved(s, tmp_path).trigger_manager
    assert [(x.variable_id, x.name) for x in saved_tm.variables if x.variable_id == 3] == [(3, "Wood left")]


def test_the_book_of_a_variable_with_no_name_adds_it(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    tm = s.scenario.trigger_manager
    _, sl = variable_part(s, at, 7)
    assert editor.ref_name(tm, "variable", 7) == "7: Variable 7"
    book(s, "Turns")
    click(s, sl, shift=True)
    editor.read_books(s)
    assert editor.ref_name(tm, "variable", 7) == "7: Turns"
    assert editor.variable_name(saved(s, tmp_path).trigger_manager, 7) == "Turns"


def test_an_empty_book_keeps_the_old_name(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    tm = s.scenario.trigger_manager
    tm.add_variable("Gold left", 3)
    _, sl = variable_part(s, at, 3)
    book(s, "")
    click(s, sl, shift=True)
    editor.read_books(s)
    assert editor.variable_name(tm, 3) == "Gold left"


def test_a_shift_click_on_an_unset_variable_gives_no_book(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    _, sl = variable_part(s, at, -1)
    sent = book(s, "x")
    click(s, sl, shift=True)
    assert not any(c.startswith("give p minecraft:writable_book") for c in sent)
