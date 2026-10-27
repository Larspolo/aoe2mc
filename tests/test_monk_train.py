"""game/train.py: an own complete monastery trains monks in the Castle Age, 100 gold and 51 AoE2 seconds as in AoE2 DE
(#1243). A trained monk does not gather: it joins the units that take the move orders (g.soldiers)."""
import re

from test_feudal_age import add
from test_loom import menus, setup

import units
from game import build, train

MONK = " 0:evoker_spawn_egg:Monk:100 gold · 51 s · "
TECHS = " 1:book:Fervor:140 gold · 50 s · research 2:book:Sanctity:175 gold · 60 s · research 3:book:Redemption:475 gold · " \
        "50 s · research" \
        " 18:book:Devotion:100 food · 200 gold · 40 s · research"      # (#1261, #1264, #1584)
RALLY = " 8:white_banner:Rally point:Click, then right click the ground"
MONASTERY = (12, 2)                                                    # a block of the monastery of add()


def monastery(gold=100, age=2):
    server, g = setup(gold=gold)
    g.techs |= set(build.AGE_TECHS[:age])
    add(g, "MONASTERY")
    return server, g


def test_the_monastery_menu_shows_the_monk_with_its_cost_and_time():
    server, g = monastery()
    assert train.open_menu(g, "Steve", MONASTERY) is not None
    assert menus(server)[-1] == "aoe menu Steve Monastery" + MONK + "queue 0/15" + TECHS + RALLY


def test_before_the_castle_age_the_monk_is_gray_and_a_click_does_nothing():
    server, g = monastery(age=1)
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert menus(server)[-1] == "aoe menu Steve Monastery 0:gray_dye:Monk:100 gold · 51 s · Needs the Castle Age" + RALLY
    assert train.order(g, "Steve", rect, 0) == 0 and g.stock["gold"] == 100 and not g.queues.get(rect)


def test_a_click_takes_100_gold_and_the_monk_comes_after_51_seconds():
    server, g = monastery(gold=150)
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, 0) == 1 and g.stock["gold"] == 50
    assert train.order(g, "Steve", rect, 0) == 0 and len(g.queues[rect]) == 1   # 50 gold is not enough
    assert train.tick(g, 50) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(rf"summon {units.classify('MONK')['id']} ", summon)
    assert train.ITEMS["MONK"][1] == units.classify("MONK")["id"].split(":")[1] + "_spawn_egg"
    assert g.soldiers[uuid] == "MONK" and uuid not in g.villagers   # a monk does not gather


def test_the_monk_has_a_help_line():
    assert train.HELP["MONK"]
