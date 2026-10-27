"""game/train.py: an open training menu shows the live queue (#1335). tick() shows it again when a unit is done and
at most once per 10 % of progress; a menu of another building or a closed menu gets no refresh."""
from test_loom import menus, setup
from test_monk_train import MONASTERY, monastery

from game import menu, train

TC = (3, 3)                                                            # a block of the town center of setup()


def test_a_done_unit_leaves_the_queue_row_of_the_open_menu():
    server, g = monastery(gold=150)
    rect = train.open_menu(g, "Steve", MONASTERY)
    train.order(g, "Steve", rect, 0)
    assert "Monk 0 %" in menus(server)[-1]
    train.tick(g, 51)
    assert not g.queues[rect] and "Monk 0 %" not in menus(server)[-1] and "queue 0/15" in menus(server)[-1]


def test_the_progress_changes_with_at_most_one_refresh_per_10_percent():
    server, g = setup(food=50)
    rect = train.open_menu(g, "Steve", TC)
    train.order(g, "Steve", rect, 0)
    n = len(menus(server))
    for _ in range(24):                                                # a villager: 25 s, 1 s steps
        train.tick(g, 1)
    shown = menus(server)[n:]
    assert 8 <= len(shown) <= 10                                       # 10 % steps: 12 %, 20 %, ... 92 %
    assert [s for s in shown if "Villager 92 %" in s] and not [s for s in shown if "Villager 4 %" in s]
    train.tick(g, 1)
    assert "Villager 9" not in menus(server)[-1] and "queue 0/15" in menus(server)[-1]


def test_a_menu_of_another_building_or_a_closed_menu_gets_no_refresh():
    server, g = monastery(gold=150)
    g.stock["food"] = 50
    tc = train.open_menu(g, "Steve", TC)
    train.order(g, "Steve", tc, 0)                                     # a villager in the town center
    train.open_menu(g, "Alex", MONASTERY)                              # Alex looks at the monastery
    menu.close(g, "Steve")
    n = len(menus(server))
    train.tick(g, 25)
    assert not g.queues[tc] and len(menus(server)) == n
