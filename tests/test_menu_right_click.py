"""A right click on a menu item (#3523): the plugin sets aoe_menu to slot + 1 + menu.RIGHT."""
from test_menu import Game

from game import menu


def test_a_handler_with_right_gets_the_right_click():
    g, got = Game({"Steve": 3 + menu.RIGHT}), []
    g.menus["Steve"] = lambda p, slot, shift, right=False: got.append((p, slot, shift, right))
    assert menu.clicks(g) == [("Steve", 2)] and got == [("Steve", 2, False, True)]
    g.scores["Steve"] = 3                                              # a normal click and a shift click stay
    g.scores["Alex"] = -3
    g.menus["Alex"] = g.menus["Steve"]
    menu.clicks(g)
    assert got[1:] == [("Steve", 2, False, False), ("Alex", 2, True, False)]


def test_a_handler_without_right_gets_a_normal_click():
    g, got = Game({"Steve": 1 + menu.RIGHT}), []
    g.menus["Steve"] = lambda p, slot, shift: got.append((p, slot, shift))
    assert menu.clicks(g) == [("Steve", 0)] and got == [("Steve", 0, False)]
