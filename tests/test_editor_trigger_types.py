"""The types of the trigger menu (#6089): a click adds each condition and effect type of the data files to a trigger of
State.scenario, a right click removes it, and `triggers <word>` shows only the matching types."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
import table  # noqa: E402
from test_editor_palette import state_of  # noqa: E402
from test_editor_triggers_menu import world_of  # noqa: E402


def click(s, slot, shift=False, right=False):
    s.menus["p"]("p", slot, shift, right=right)


def opened(s):
    editor.triggers_menu(s, "p")
    click(s, editor.ADD)
    at = len(s.scenario.trigger_manager.triggers) - 1
    editor.triggers_menu(s, "p", at // editor.PAGE, at)
    return at, s.scenario.trigger_manager.triggers[at]


def test_a_click_adds_each_type(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, t = opened(s)
    for kind, slot in (("condition", editor.NEW_CONDITION), ("effect", editor.NEW_EFFECT)):
        names = [r["name"] for r in table.load(os.path.join(editor.CONVERTER_DATA, editor.KINDS[kind]))]
        for i, name in enumerate(names):
            editor.triggers_menu(s, "p", at // editor.PAGE, at)
            click(s, slot)
            page, k = divmod(i, editor.PAGE)
            for _ in range(page):
                click(s, editor.PAGE + 8)
            click(s, k)
        got = [n for k, _, n in editor.parts(t) if k == kind]
        assert [n.rstrip("_") for n in got] == names, kind
    assert s.edited


def test_a_right_click_removes(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, t = opened(s)
    click(s, editor.NEW_CONDITION)
    click(s, 0)
    click(s, editor.NEW_EFFECT)
    click(s, 0)
    assert len(t.conditions) == 1 and len(t.effects) == 1
    click(s, editor.PARTS)                                           # a left click removes nothing (P9)
    assert len(t.conditions) == 1
    editor.triggers_menu(s, "p", at // editor.PAGE, at)              # it opens the fields (#6090): back to the trigger
    click(s, editor.PARTS, right=True)
    assert not t.conditions and len(t.effects) == 1
    click(s, editor.PARTS, right=True)
    assert not t.effects


def test_a_word_shows_the_matching_types(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    rows = editor.trigger_types(tuple(editor.KINDS), "timer")
    assert rows and all("timer" in n.lower() for _, n, _ in rows)
    assert len(rows) < len(editor.trigger_types(tuple(editor.KINDS)))
    editor.triggers_menu(s, "p", word="timer")
    t = s.scenario.trigger_manager.triggers[-1]
    before = len(editor.parts(t))
    click(s, 0)
    assert len(editor.parts(t)) == before + 1 and "TIMER" in editor.parts(t)[-1][2]
    assert editor.TRIGGERS.search("INFO]: <p> triggers timer").group(2) == "timer"
