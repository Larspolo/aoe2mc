"""The name and the description of a trigger in the editor (#6111): a click gives a book, the book sets the text, and
an empty name keeps the old one."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from test_editor_palette import state_of  # noqa: E402
from test_editor_trigger_types import click, opened  # noqa: E402
from test_editor_triggers_menu import saved, world_of  # noqa: E402


def book(s, text):
    """Make the books of s read as text (a book of a text field)."""
    sent = []
    s.command = lambda c: sent.append(c) or (f'p has the following entity data: [{{raw:"{text}"}}]'  # noqa: E731
                                            if c.startswith("data get") and "aoe_field" in c else "")
    return sent


def test_the_name_book_sets_the_name_and_the_save_has_it(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, t = opened(s)
    sent = book(s, "Hunt")
    click(s, editor.NAME)
    assert any(c.startswith("give p minecraft:writable_book") and f"{at}.name" in c for c in sent)
    editor.read_books(s)
    assert t.name == "Hunt"
    assert saved(s, tmp_path).trigger_manager.triggers[at].name == "Hunt"


def test_the_description_book_sets_the_description(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, t = opened(s)
    sent = book(s, "Gather wood")
    click(s, editor.DESCRIPTION)
    assert any(c.startswith("give p minecraft:writable_book") and f"{at}.description" in c for c in sent)
    editor.read_books(s)
    assert t.description == "Gather wood"
    assert saved(s, tmp_path).trigger_manager.triggers[at].description == "Gather wood"


def test_an_empty_book_keeps_the_old_name(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, t = opened(s)
    old = t.name
    book(s, "")
    click(s, editor.NAME)
    editor.read_books(s)
    assert t.name == old
