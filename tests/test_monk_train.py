"""game/train.py: an own complete monastery trains monks in the Castle Age, with the AoE2 DE cost and time of the data
(#1243). A trained monk does not gather: it joins the units that take the move orders (g.soldiers)."""
import re

from menu_line import items, labels, order
from test_feudal_age import add
from test_loom import menus, setup

import units
from game import build, train

MONASTERY = (12, 2)                                                    # a block of the monastery of add()


def monastery(gold=100, age=2):
    server, g = setup(gold=gold)
    g.techs |= set(build.AGE_TECHS[:age])
    add(g, "MONASTERY")
    return server, g


def test_the_monastery_menu_has_the_items_of_the_data_in_their_order():
    server, g = monastery()
    assert train.open_menu(g, "Steve", MONASTERY) is not None
    menu = menus(server)[-1]                                       # the Castle Age technologies after them (#1582)
    assert menu.startswith("aoe menu Steve Monastery ") and labels(menu) == order(g, "MONASTERY")


def test_before_the_castle_age_the_monk_is_gray_and_a_click_does_nothing():
    server, g = monastery(age=1)
    rect = train.open_menu(g, "Steve", MONASTERY)
    menu = menus(server)[-1]
    shown = [s for s in items(menu) if not s.startswith(f"{train.RALLY[0]}:{train.RALLY[1]}:")]
    assert shown and labels(menu) == order(g, "MONASTERY")         # no civ: all units (#1939)
    assert all(s.split(":")[1] == build.LOCKED and s.endswith(" · Needs the Castle Age") for s in shown), shown
    assert train.order(g, "Steve", rect, train.SLOTS["MONK"]) == 0 and g.stock["gold"] == 100 and not g.queues.get(rect)


def test_a_click_takes_the_gold_and_the_monk_comes_after_its_time():
    cost = train.COSTS["MONK"]["gold"]
    server, g = monastery(gold=cost + cost // 2)
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, train.SLOTS["MONK"]) == 1 and g.stock["gold"] == cost // 2
    assert train.order(g, "Steve", rect, train.SLOTS["MONK"]) == 0 and len(g.queues[rect]) == 1   # not enough gold
    assert train.tick(g, train.seconds(g, "MONK", "MONASTERY") - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(rf"summon {units.classify('MONK')['id']} ", summon)
    assert train.ITEMS["MONK"][1] == units.classify("MONK")["id"].split(":")[1] + "_spawn_egg"
    assert g.soldiers[uuid] == "MONK" and uuid not in g.villagers   # a monk does not gather


def test_the_monk_has_a_help_line():
    assert train.HELP["MONK"]
