"""game/train.py: the town center menu has "Feudal Age" at its cost and time. It needs 2 types of Dark Age buildings;
after the research the sidebar title shows the age, all players see it, and the item leaves the menu (#672)."""
from menu_line import item
from test_castle_upgrades import entry as text
from test_loom import menus, setup

from game import train

AGE = "FEUDAL_AGE"
# .get: the Antiquity rules have other ages, and their tests import the helpers of this file
SLOT, COST, TIME = train.ITEMS.get(AGE, (None,))[0], train.COSTS.get(AGE, {}).get("food", 0), train.TRAIN_TIMES.get(AGE, 0)


def entry(g, name, state, icon=None):
    """The menu item of name with its cost and time for the player of g."""
    slot, item, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f"{slot}:{icon or item}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def add(g, *names):
    for i, name in enumerate(names):                                   # complete own buildings away from the units
        g.data["objects"].append({"kind": "building", "name": name, "player": 1, "tile": [12.5, 2.5 + 3 * i],
                                  "footprint": [11, 1 + 3 * i, 14, 4 + 3 * i]})


def test_without_two_dark_age_buildings_the_item_says_what_is_missing_and_a_click_does_nothing():
    server, g = setup(food=1000)
    add(g, "LUMBER_CAMP", "LUMBER_CAMP", "HOUSE")                       # one type, and a house does not count
    rect = train.open_menu(g, "Steve", (3, 3))
    feudal = item(menus(server)[-1], "Feudal Age")
    assert feudal.startswith(entry(g, AGE, "needs 2 of ")) and feudal.endswith(" (1/2)")
    assert item(menus(server)[-1], "Castle Age") == text(g, (3, 3), "CASTLE_AGE") + "Needs the Feudal Age"
    assert train.order(g, "Steve", rect, SLOT) == 0 and g.stock["food"] == 1000 and not g.queues.get(rect)
    assert any("Feudal Age needs 2 of" in c for c in server.log)


def test_a_built_mill_completes_the_need_and_a_click_queues_the_age_once():
    server, g = setup(food=1000)
    add(g, "BARRACKS")
    g.sites.append({"name": "MILL", "player": 1, "footprint": [11, 10, 13, 12], "done": True})
    rect = train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Feudal Age") == entry(g, AGE, "research")
    assert train.order(g, "Steve", rect, SLOT, shift=True) == 1 and g.stock["food"] == 1000 - COST
    assert train.order(g, "Steve", rect, SLOT) == 0 and g.stock["food"] == 1000 - COST
    assert item(menus(server)[-1], "Feudal Age") == entry(g, AGE, "researching")


def test_after_its_time_the_player_is_in_the_feudal_age():
    server, g = setup(food=COST)
    add(g, "MINING_CAMP", "DOCK")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert 'scoreboard objectives modify aoe_res displayname "Resources (Dark Age)"' in server.log
    train.order(g, "Steve", rect, SLOT)
    train.tick(g, TIME - 1)
    assert train.age(g) == "Dark Age"
    train.tick(g, 1)
    assert train.age(g) == "Feudal Age" and "FEUDAL_AGE" in g.techs and not g.queues.get(rect)
    assert server.log.count('scoreboard objectives modify aoe_res displayname "Resources (Feudal Age)"') == 1
    assert 'title @a[team=p1] title {"text": "Feudal Age", "color": "gold"}' in server.log
    assert any(c.startswith("tellraw @a") and '"fallback": "Feudal Age"}]' in c for c in server.log)
    assert any(c.startswith("playsound minecraft:ui.toast.challenge_complete") for c in server.log)
    train.show(g, "Steve", rect)
    assert "Feudal Age" not in menus(server)[-1].split("Town Center", 1)[1]
