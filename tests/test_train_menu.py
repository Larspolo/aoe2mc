"""game/train.py: a right click on the own town center opens its menu; a click on "Villager" queues 1, a shift click 5,
and the menu stays open with the new queue count (#620)."""
from urllib.parse import unquote

from menu_line import item, labels, order
from test_train import setup

from game import train

FOOD = train.COSTS["VILLAGER_MALE"]["food"]
RALLY = "8:white_banner:Rally point:Click, then right click the ground"   # the last item (#707)


def menus(server):
    """The decoded "aoe menu" commands that the server got."""
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def entry(g, rect, name):
    """The menu text of name in the building rect up to its state, from the data: slot, item, label, cost and time."""
    building = train.homes(g)[rect]
    slot, icon, label = train.layout(g, rect)[name]
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free"
    icon = train.build.LOCKED if train.build.locked(g, name) else icon
    return f"{slot}:{icon}:{label}:{cost} · {round(train.seconds(g, name, building), 1):g} s · "


def check_items(g, rect, cmd):
    """Each unit and technology item of cmd has the text of the data, and the rally point is the last item."""
    for name, (_, _, label) in train.layout(g, rect).items():
        assert (item(cmd, label) or "").startswith(entry(g, rect, name)), name
    assert item(cmd, "Rally point") == RALLY


def test_a_right_click_on_the_town_center_opens_its_menu():
    server, g = setup()
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Town Center ") and labels(cmd) == order(g, "TOWN_CENTER")   # the full menu
    check_items(g, (2, 5, 2, 5), cmd)
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
    assert len(g.queues[2, 5, 2, 5]) == 5 and g.stock["food"] == 1000 - 5 * FOOD
    assert item(menus(server)[-1], "Villager").endswith(" queue 5/15")


def test_a_shift_click_queues_as_many_as_the_food_and_the_queue_allow():
    server, g = setup(food=3 * FOOD + 10)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 0, shift=True) == 3 and g.stock["food"] == 10
    assert sum(f"{FOOD} food" in c for c in server.log if c.startswith("tellraw Steve")) == 1   # one message
    g.stock["food"] = 10000
    for _ in range(3):                                                 # 3 + 5 + 5 + 2: the queue is full
        train.order(g, "Steve", rect, 0, shift=True)
    assert len(g.queues[rect]) == train.QUEUE == 15
    assert train.order(g, "Steve", rect, 0) == 0 and any("queue is full" in c for c in server.log)
    assert item(menus(server)[-1], "Villager").endswith(" queue 15/15")


def test_a_click_on_an_empty_slot_queues_nothing():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    used = {slot for slot, _, _ in train.layout(g, rect).values()} | {train.RALLY[0]}
    empty = min(set(range(train.ROW)) - used)
    assert train.order(g, "Steve", rect, empty) == 0 and g.stock["food"] == 1000
