"""game/train.py: a spam click on the town center opens its menu once; the uses that came before the menu showed
open no second menu after the player closes it (#3267, owner feedback)."""
from test_train import setup
from test_train_menu import menus

from game import menu, train


def test_several_right_clicks_open_the_menu_once():
    server, g = setup()
    t = [0.0]
    g.clock = lambda: t[0]
    for _ in range(4):                                                 # one use in each call, as in a spam click
        server.scores["aoe_use"] = 1
        for name in g.clicks():
            g.click(name)
        t[0] += 0.2
    assert len(menus(server)) == 1


def test_no_second_open_after_the_menu_closes():
    server, g = setup()
    t = [0.0]
    g.clock = lambda: t[0]
    assert train.open_menu(g, "Steve", (3, 3), True) and len(menus(server)) == 1
    menu.close(g, "Steve")
    t[0] = 0.5
    assert train.open_menu(g, "Steve", (3, 3), True) and len(menus(server)) == 1 and "Steve" not in g.menus
    t[0] = 0.5 + train.SPAM                                           # a new click later opens it again
    assert train.open_menu(g, "Steve", (3, 3), True) and len(menus(server)) == 2
