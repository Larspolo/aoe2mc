"""game/train.py: a right click on the own town center opens its menu; a click on "Villager" queues 1, a shift click 5,
and the menu stays open with the new queue count (#620)."""
from urllib.parse import unquote

from menu_line import item, labels, order
from test_train import setup

from game import train

VILLAGER = "0:villager_spawn_egg:Villager:50 food · 25 s · queue 0/15"
LOOM = "1:book:Loom:50 gold · 25 s · research"
IMPERIAL = "5:gray_dye:Imperial Age:1000 food · 800 gold · 190 s · Needs the Castle Age"   # gray before it (#1081)
CASTLE = "4:gray_dye:Castle Age:800 food · 200 gold · 160 s · Needs the Feudal Age"   # the next ages: gray (#1080)
FEUDAL = "2:bell:Feudal Age:500 food · 130 s · needs 2 of barracks, mill, lumber camp, mining camp, dock (0/2)"   # (#672)
RALLY = "8:white_banner:Rally point:Click, then right click the ground"   # the last item (#707)
SPEAR = "1:gray_dye:Spearman:35 food · 25 wood · 22 s · Needs the Feudal Age"   # in the Dark Age barracks menu (#729)
SKIRM = "1:drowned_spawn_egg:Skirmisher:25 food · 35 wood · 22 s · queue 0/15"   # in the archery range menu (#730)


def menus(server):
    """The decoded "aoe menu" commands that the server got."""
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_a_right_click_on_the_town_center_opens_its_menu():
    server, g = setup()
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Town Center ") and labels(cmd) == order(g, "TOWN_CENTER")   # the full menu
    assert [item(cmd, label) for label in ("Villager", "Loom", "Feudal Age", "Castle Age", "Imperial Age", "Rally point")] \
        == [VILLAGER, LOOM, FEUDAL, CASTLE, IMPERIAL, RALLY]
    assert "Steve" in g.menus and g.stock["food"] == 60 and not any(g.queues.values())


def test_no_menu_at_the_town_center_of_another_player_or_on_the_ground():
    server, g = setup()
    assert train.open_menu(g, "Steve", (18, 18)) is None and train.open_menu(g, "Steve", (10, 10)) is None
    assert not menus(server) and not g.menus


def test_a_click_queues_one_and_the_menu_shows_the_new_count():
    server, g = setup(food=1000)
    train.open_menu(g, "Steve", (3, 3))
    server.scores["aoe_menu"] = 1
    g.clicks()
    assert item(menus(server)[-1], "Villager").endswith(" queue 1/15") and "Steve" in g.menus   # the menu stays open


def test_a_shift_click_queues_five():
    server, g = setup(food=1000)
    train.open_menu(g, "Steve", (3, 3))
    server.scores["aoe_menu"] = -1                                     # the plugin: -(slot + 1) for a shift click
    g.clicks()
    assert len(g.queues[2, 5, 2, 5]) == 5 and g.stock["food"] == 750
    assert item(menus(server)[-1], "Villager").endswith(" queue 5/15")


def test_a_shift_click_queues_as_many_as_the_food_and_the_queue_allow():
    server, g = setup(food=160)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 0, shift=True) == 3 and g.stock["food"] == 10
    assert sum("50 food" in c for c in server.log if c.startswith("tellraw Steve")) == 1   # one message
    g.stock["food"] = 10000
    for _ in range(3):                                                 # 3 + 5 + 5 + 2: the queue is full
        train.order(g, "Steve", rect, 0, shift=True)
    assert len(g.queues[rect]) == train.QUEUE == 15
    assert train.order(g, "Steve", rect, 0) == 0 and any("queue is full" in c for c in server.log)
    assert item(menus(server)[-1], "Villager").endswith(" queue 15/15")


def test_a_click_on_an_empty_slot_queues_nothing():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 7) == 0 and g.stock["food"] == 1000
