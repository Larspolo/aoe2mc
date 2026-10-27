"""game/train.py: the town center menu has "Feudal Age" (500 food, 130 AoE2 seconds). It needs 2 types of Dark Age
buildings; after the research the sidebar title shows the age, all players see it, and the item leaves the menu (#672)."""
from test_loom import menus, setup
from test_train_menu import CASTLE, RALLY

from game import train


def add(g, *names):
    for i, name in enumerate(names):                                   # complete own buildings away from the units
        g.data["objects"].append({"kind": "building", "name": name, "player": 1, "tile": [12.5, 2.5 + 3 * i],
                                  "footprint": [11, 1 + 3 * i, 14, 4 + 3 * i]})


def test_without_two_dark_age_buildings_the_item_says_what_is_missing_and_a_click_does_nothing():
    server, g = setup(food=1000)
    add(g, "LUMBER_CAMP", "LUMBER_CAMP", "HOUSE")                       # one type, and a house does not count
    rect = train.open_menu(g, "Steve", (3, 3))
    assert menus(server)[-1].endswith(" 2:bell:Feudal Age:500 food · 130 s · "
                                      "needs 2 of barracks, mill, lumber camp, mining camp, dock (1/2)" + CASTLE + RALLY)
    assert train.order(g, "Steve", rect, 2) == 0 and g.stock["food"] == 1000 and not g.queues.get(rect)
    assert any("Feudal Age needs 2 of" in c for c in server.log)


def test_a_built_mill_completes_the_need_and_a_click_queues_the_age_once():
    server, g = setup(food=1000)
    add(g, "BARRACKS")
    g.sites.append({"name": "MILL", "player": 1, "footprint": [11, 10, 13, 12], "done": True})
    rect = train.open_menu(g, "Steve", (3, 3))
    assert menus(server)[-1].endswith(" 2:bell:Feudal Age:500 food · 130 s · research" + CASTLE + RALLY)
    assert train.order(g, "Steve", rect, 2, shift=True) == 1 and g.stock["food"] == 500
    assert train.order(g, "Steve", rect, 2) == 0 and g.stock["food"] == 500
    assert menus(server)[-1].endswith(" 2:bell:Feudal Age:500 food · 130 s · researching" + CASTLE + RALLY)


def test_after_130_seconds_the_player_is_in_the_feudal_age():
    server, g = setup(food=500)
    add(g, "MINING_CAMP", "DOCK")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert 'scoreboard objectives modify aoe_res displayname "Resources (Dark Age)"' in server.log
    train.order(g, "Steve", rect, 2)
    train.tick(g, 129)
    assert train.age(g) == "Dark Age"
    train.tick(g, 1)
    assert train.age(g) == "Feudal Age" and "FEUDAL_AGE" in g.techs and not g.queues.get(rect)
    assert server.log.count('scoreboard objectives modify aoe_res displayname "Resources (Feudal Age)"') == 1
    assert 'title @a[team=p1] title {"text": "Feudal Age", "color": "gold"}' in server.log
    assert any(c.startswith("tellraw @a") and "Player 1 advances to the Feudal Age." in c for c in server.log)
    assert any(c.startswith("playsound minecraft:ui.toast.challenge_complete") for c in server.log)
    train.show(g, "Steve", rect)
    assert "Feudal Age" not in menus(server)[-1].split("Town Center", 1)[1]
