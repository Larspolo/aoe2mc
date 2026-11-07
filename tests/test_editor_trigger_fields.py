"""The fields of trigger conditions and effects in the editor (#6090): clicks set the number, player, on/off and list
fields of each type (the attributes of the parser), a book sets a text field, and the save has the values."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import table  # noqa: E402
from test_editor_palette import state_of  # noqa: E402
from test_editor_trigger_types import click, opened  # noqa: E402
from test_editor_triggers_menu import saved, world_of  # noqa: E402


def add(s, at, kind, name):
    """Add a part of type name to trigger at and open its fields; returns the part."""
    t = s.scenario.trigger_manager.triggers[at]
    editor.add_part(t, kind, name)
    index = len(editor.parts(t)) - 1
    editor.fields_menu(s, "p", at, index)
    return editor.parts(t)[index][1]


def slot(kind, part, attr):
    return [a for a, _ in editor.fields(kind, part)].index(attr)


def test_timer_and_send_chat_fields_are_saved(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    timer = add(s, at, "condition", "TIMER")
    start = max(timer.timer, -1)
    click(s, slot("condition", timer, "timer"), shift=True)
    click(s, slot("condition", timer, "timer"))
    assert timer.timer == start + 11
    chat = add(s, at, "effect", "SEND_CHAT")
    click(s, slot("effect", chat, "source_player"))
    player = chat.source_player
    sent = []
    s.command = lambda c: sent.append(c) or ('p has the following entity data: [{raw:"Hello"}]'   # noqa: E731
                                            if c.startswith("data get") and "aoe_field" in c else "")
    click(s, slot("effect", chat, "message"))
    assert any(c.startswith("give p minecraft:writable_book") and "aoe_field" in c for c in sent)
    editor.read_books(s)
    assert chat.message == "Hello"
    t = saved(s, tmp_path).trigger_manager.triggers[at]
    assert t.conditions[-1].timer == start + 11
    assert t.effects[-1].message == "Hello" and t.effects[-1].source_player == player


def test_each_field_of_each_type_changes_by_a_click(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    seen = set()
    for kind in editor.KINDS:
        for r in table.load(os.path.join(editor.CONVERTER_DATA, editor.KINDS[kind])):
            part = add(s, at, kind, r["name"])
            for i, (a, form) in enumerate(editor.fields(kind, part)):
                seen.add(form)
                if form == "text":
                    continue
                before = getattr(part, a)
                editor.fields_menu(s, "p", at, len(editor.parts(s.scenario.trigger_manager.triggers[at])) - 1)
                click(s, i)
                assert getattr(part, a) != before, (r["name"], a, form, before)
    assert {"number", "player", "bool", "text"} <= seen and len(seen) > 4
