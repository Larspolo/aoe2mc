"""The search of the palette (#6058): `palette <word>` shows the objects of all tabs whose name has the word."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import build  # noqa: E402
import editor  # noqa: E402
import menu  # noqa: E402


class Fake:
    def __init__(self):
        self.sent, self.picked, self.shown = [], {}, None
        self.look = lambda p: None

    def command(self, c):
        self.sent.append(c)


def test_the_chat_word_takes_a_word():
    line = "[12:00:00 INFO]: <p> palette Joan"
    assert editor.PALETTE.search(line).groups() == ("p", "Joan")
    assert editor.PALETTE.search("[12:00:00 INFO]: <p> palette").groups() == ("p", None)


def test_a_word_of_a_hero_finds_it_and_no_match_gives_the_text(monkeypatch):
    g = Fake()
    monkeypatch.setattr(menu, "show", lambda g, p, title, items, click: setattr(g, "shown", (items, click)) or True)
    hero = dict(editor.tabs())["heroes"][0]
    word = max(build.pretty(hero).split(), key=len)
    assert editor.open_menu(g, "p", word=word.upper())
    items, click = g.shown
    assert build.pretty(hero) in [i[2] for i in items[:editor.PAGE]]
    slot = next(i[0] for i in items if i[2] == build.pretty(hero))
    click("p", slot, False)
    assert g.picked["p"] == hero
    g.shown = None
    assert editor.open_menu(g, "p", word="qqzzxq") is None and g.shown is None
    assert g.sent and g.sent[-1].startswith("tellraw p ") and "qqzzxq" in g.sent[-1]
