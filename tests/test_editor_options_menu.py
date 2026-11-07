"""The options menu of the editor (#6085): a click disables a technology, building or unit of the current player."""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402


class Fake:
    def __init__(self):
        self.sent, self.menus, self.player, self.data = [], {}, 2, {"players": {}}

    def command(self, cmd):
        self.sent.append(cmd)
        return ""


def names(g):
    return g.data["players"]["2"].get("disabled", [])


def test_a_click_toggles_an_item_of_each_tab(monkeypatch):
    monkeypatch.setattr(editor, "icons", lambda: {})
    g = Fake()
    for tab in range(len(editor.OPTION_TABS)):
        editor.options_menu(g, "p", tab)
        first = editor.option_names(tab)[0]
        g.menus["p"]("p", 0, False)
        assert first in names(g) and names(g) == sorted(names(g))
        g.menus["p"]("p", 0, False)
        assert first not in names(g)


def test_a_disabled_item_shows_a_barrier(monkeypatch):
    monkeypatch.setattr(editor, "icons", lambda: {})
    shown = {}
    monkeypatch.setattr(editor.menu, "show", lambda g, p, title, items, h: (shown.update(items=items), g.menus.update({p: h})))
    g = Fake()
    editor.options_menu(g, "p", 1)
    g.menus["p"]("p", 0, False)
    first = shown["items"][0]
    assert first[1] == "barrier" and first[3] == "Disabled"
    assert shown["items"][1][1] != "barrier"


def test_run_opens_the_menu_for_the_chat_word(monkeypatch):
    seen = []
    monkeypatch.setattr(editor, "options_menu", lambda s, p: seen.append(p))
    monkeypatch.setattr(editor, "words", lambda game, n: (n, 0))
    monkeypatch.setattr(editor.time, "sleep", lambda s: None)
    game = types.SimpleNamespace(server=types.SimpleNamespace(log=[]),
                                 command=lambda c: "")
    state = types.SimpleNamespace(look=lambda p: None)
    monkeypatch.setattr(editor, "tick", lambda s: game.server.log.append("[12:00:00 INFO]: <steve> options"))  # after the start
    runs = iter([True, False])
    editor.run(game, "out", lambda: next(runs), state)
    assert seen == ["steve"]
