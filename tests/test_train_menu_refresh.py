"""game/train.py: an open training menu shows the live queue (#1335). tick() shows it again when a unit is done and
at most once per 10 % of progress; a menu of another building or a closed menu gets no refresh."""
from test_loom import menus, setup
from test_monk_train import MONASTERY, monastery

from game import menu, train

TC = (3, 3)                                                            # a block of the town center of setup()
MONK, GOLD = train.ITEMS["MONK"][2], train.COSTS["MONK"].get("gold", 0)
VILLAGER, FOOD = train.ITEMS["VILLAGER_MALE"][2], train.COSTS["VILLAGER_MALE"].get("food", 0)


def test_a_done_unit_leaves_the_queue_row_of_the_open_menu():
    server, g = monastery(gold=GOLD)
    rect = train.open_menu(g, "Steve", MONASTERY)
    train.order(g, "Steve", rect, train.layout(g, rect)["MONK"][0])
    assert f"{MONK} 0 %" in menus(server)[-1]
    train.tick(g, train.TRAIN_TIMES["MONK"])
    assert not g.queues[rect] and f"{MONK} 0 %" not in menus(server)[-1] and "queue 0/15" in menus(server)[-1]


def test_the_progress_changes_with_at_most_one_refresh_per_10_percent():
    server, g = setup(food=FOOD)
    rect = train.open_menu(g, "Steve", TC)
    train.order(g, "Steve", rect, train.layout(g, rect)["VILLAGER_MALE"][0])
    n = len(menus(server))
    step = train.TRAIN_TIMES["VILLAGER_MALE"] / 25                     # 4 % of the train time
    for _ in range(24):
        train.tick(g, step)
    shown = menus(server)[n:]
    assert 8 <= len(shown) <= 10                                       # 10 % steps: 12 %, 20 %, ... 92 %
    assert [s for s in shown if f"{VILLAGER} 92 %" in s] and not [s for s in shown if f"{VILLAGER} 4 %" in s]
    train.tick(g, step)
    assert f"{VILLAGER} 9" not in menus(server)[-1] and "queue 0/15" in menus(server)[-1]


def test_a_menu_of_another_building_or_a_closed_menu_gets_no_refresh():
    server, g = monastery(gold=GOLD)
    g.stock["food"] = FOOD
    tc = train.open_menu(g, "Steve", TC)
    train.order(g, "Steve", tc, train.layout(g, tc)["VILLAGER_MALE"][0])   # a villager in the town center
    train.open_menu(g, "Alex", MONASTERY)                              # Alex looks at the monastery
    menu.close(g, "Steve")
    n = len(menus(server))
    train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])
    assert not g.queues[tc] and len(menus(server)) == n
