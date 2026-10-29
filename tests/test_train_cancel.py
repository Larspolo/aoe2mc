"""game/train.py: the second row of a training menu shows the queue; a click on a queued unit cancels it and gives
back its cost (#706)."""
import shutil

import pytest
from test_train import setup
from test_train_menu import menus

from game import menu, train

RECT = (2, 5, 2, 5)
FOOD = train.COSTS["VILLAGER_MALE"]["food"]


def test_the_second_row_shows_the_queue_in_order():
    server, g = setup(food=1000)
    g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    (_, *v), (loom, *lm) = (train.layout(g, rect)[n] for n in ("VILLAGER_MALE", "LOOM"))
    train.order(g, "Steve", rect, 0)
    train.order(g, "Steve", rect, 0)
    train.order(g, "Steve", rect, loom)
    train.order(g, "Steve", rect, 0)
    g.queues[rect][0]["progress"] = 0.4
    train.show(g, "Steve", rect)
    R = train.ROW
    assert (f" {R}:{v[0]}:{v[1]} 40 %:Click: cancel 1:2 {R + 1}:{lm[0]}:{lm[1]}:Click: cancel 1"
            f" {R + 2}:{v[0]}:{v[1]}:Click: cancel 1 ") in menus(server)[-1]   # the queue row first
    assert train.groups(g.queues[rect]) == [("VILLAGER_MALE", 0, 2), ("LOOM", 2, 1), ("VILLAGER_MALE", 3, 1)]


def test_a_click_on_a_queued_unit_cancels_the_last_of_its_group_and_gives_back_its_cost():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, 0, shift=True)                       # 5 villagers
    g.queues[rect][0]["progress"] = 0.5
    server.scores["aoe_menu"] = train.ROW + 1                          # a click on slot 9: the plugin sends slot + 1
    g.clicks()
    assert len(g.queues[rect]) == 4 and g.queues[rect][0]["progress"] == 0.5   # the unit in training goes on
    assert g.stock["food"] == 1000 - 4 * FOOD and f"scoreboard players add Food aoe_res {FOOD}" in server.log
    assert ":Click: cancel 1:4 0:" in menus(server)[-1] and "Steve" in g.menus   # the menu shows the new queue


def test_the_unit_in_training_gives_back_its_full_cost():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, 0)
    g.queues[rect][0]["progress"] = 0.9
    assert train.cancel(g, "Steve", rect, 0) == "VILLAGER_MALE"
    assert g.queues[rect] == [] and g.stock["food"] == 1000
    train.show(g, "Steve", rect)
    assert " 9:" not in menus(server)[-1]                              # an empty queue: no queue items


def test_a_click_on_an_empty_queue_slot_changes_nothing():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, 0)
    assert train.order(g, "Steve", rect, train.ROW + 3) == 0
    assert len(g.queues[rect]) == 1 and g.stock["food"] == 1000 - FOOD


def test_menu_item_count():
    cmd = menu.command("Steve", "Barracks", [(9, "zombie_spawn_egg", "Militia", "", 3), (0, "book", "Loom", "", 1)])
    assert cmd == "aoe menu Steve Barracks 9:zombie_spawn_egg:Militia::3 0:book:Loom:"


@pytest.mark.mc
def test_the_plugin_takes_the_item_count(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        good = menu.command("@a", "Barracks", [(0, "zombie_spawn_egg", "Militia", ""),
                                               (9, "zombie_spawn_egg", "Militia 40 %", "Click: cancel 1", 15)])
        assert game.command(good).strip() == "Menu: 0 players"
        for bad in ("0", "100", "x"):
            assert game.command(f"aoe menu @a Barracks 9:zombie_spawn_egg:Militia::{bad}").startswith("Bad item")
