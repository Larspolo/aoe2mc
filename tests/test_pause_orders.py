"""#3376: while the game is paused, a click gives no order and opens no menu; the Game menu still opens."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import json

import diplomacy  # noqa: E402
import gather  # noqa: E402

from game import lang


def fake():
    g = object.__new__(gather.Gather)
    g.game = types.SimpleNamespace()
    g.looks, g.grouping, g.wands, g.rallying, g.ordering = {}, {}, set(), {}, {}
    g.commands, g.orders = [], []
    g.command = lambda c: g.commands.append(c) or ""
    g.look = lambda name: ((0, 0, 0), (1, 0, 0))
    g.target = lambda eye, d, pos: g.orders.append("target") or (_ for _ in ()).throw(Reached())
    g.positions = lambda ids: {}
    g.pickable = lambda: ()
    g.map = types.SimpleNamespace(pick_ground=lambda e, d: None, pick_tree=lambda e, d: None)
    return g


class Reached(Exception):
    """The click reached the order code (target)."""


PAUSED = "title P1 actionbar " + json.dumps(lang.text("aoe2mc.gather.paused"))


def test_a_paused_click_gives_the_message_and_no_order():
    g = fake()
    g.paused = True
    g.wands.add("P1")
    g.grouping["P1"] = (1, False)
    g.click("P1")
    assert g.commands == [PAUSED] and g.orders == [] and not g.wands and not g.grouping


def test_after_continue_the_click_works_again():
    g = fake()
    g.paused = True
    g.click("P1")
    g.paused = False
    g.commands.clear()
    with pytest.raises(Reached):
        g.click("P1")
    assert PAUSED not in g.commands and g.orders == ["target"]


def test_the_game_menu_still_opens(monkeypatch):
    g = fake()
    g.paused = True
    shown = []
    monkeypatch.setattr(diplomacy.menu, "show", lambda g, p, title, items, cb: shown.append(title))
    diplomacy.open_menu(g, "P1")
    assert shown == ["Game menu"]
