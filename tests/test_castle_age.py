"""game/train.py: the town center menu has "Castle Age". Before the Feudal Age the item is gray; then it needs 2 types
of Feudal Age buildings; after the research the sidebar title shows the Castle Age, all players see it, and the item
leaves the menu (#1080)."""
from test_castle_upgrades import entry
from test_feudal_age import add
from menu_line import item
from test_loom import menus, setup

from game import train

SLOT = train.ITEMS["CASTLE_AGE"][0]


def test_in_the_dark_age_the_item_is_gray_and_a_click_does_nothing():
    server, g = setup(food=1000, gold=1000)
    add(g, "ARCHERY_RANGE", "STABLE")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Castle Age") == entry(g, (3, 3), "CASTLE_AGE") + "Needs the Feudal Age"
    assert train.order(g, "Steve", rect, SLOT) == 0 and (g.stock["food"], g.stock["gold"]) == (1000, 1000)
    assert not g.queues.get(rect) and any("Castle Age: Needs the Feudal Age." in c for c in server.log)


def test_in_the_feudal_age_the_item_says_what_is_missing_and_a_click_does_nothing():
    server, g = setup(food=1000, gold=1000)
    g.techs.add("FEUDAL_AGE")
    add(g, "BARRACKS", "MILL", "BLACKSMITH")                            # Dark Age buildings do not count
    rect = train.open_menu(g, "Steve", (3, 3))
    text = item(menus(server)[-1], "Castle Age")
    assert text.startswith(entry(g, (3, 3), "CASTLE_AGE") + "needs ") and text.endswith(" (1/2)")
    assert item(menus(server)[-1], "Imperial Age") == entry(g, (3, 3), "IMPERIAL_AGE") + "Needs the Castle Age"
    assert train.order(g, "Steve", rect, SLOT) == 0 and g.stock["food"] == 1000 and not g.queues.get(rect)
    assert any("Castle Age needs 2 of" in c for c in server.log)


def test_two_feudal_age_buildings_complete_the_need_and_a_click_queues_the_age_once():
    server, g = setup(food=1000, gold=1000)
    g.techs.add("FEUDAL_AGE")
    add(g, "STABLE")
    g.sites.append({"name": "MARKET", "player": 1, "footprint": [11, 10, 13, 12], "done": True})
    rect = train.open_menu(g, "Steve", (3, 3))
    head, cost = entry(g, (3, 3), "CASTLE_AGE"), train.price(g, "CASTLE_AGE")
    left = (1000 - cost.get("food", 0), 1000 - cost.get("gold", 0))
    assert item(menus(server)[-1], "Castle Age") == head + "research"
    assert train.order(g, "Steve", rect, SLOT, shift=True) == 1 and (g.stock["food"], g.stock["gold"]) == left
    assert train.order(g, "Steve", rect, SLOT) == 0 and (g.stock["food"], g.stock["gold"]) == left
    assert item(menus(server)[-1], "Castle Age") == head + "researching"


def test_after_its_research_time_the_player_is_in_the_castle_age():
    server, g = setup(food=10000, gold=10000)
    g.techs.add("FEUDAL_AGE")
    add(g, "ARCHERY_RANGE", "BLACKSMITH")
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, SLOT)
    train.tick(g, train.seconds(g, "CASTLE_AGE") - 1)
    assert train.age(g) == "Feudal Age"
    train.tick(g, 1)
    assert train.age(g) == "Castle Age" and "CASTLE_AGE" in g.techs and not g.queues.get(rect)
    assert server.log.count('scoreboard objectives modify aoe_res displayname "Resources (Castle Age)"') == 1
    assert 'title @a[team=p1] title {"text": "Castle Age", "color": "gold"}' in server.log
    assert any(c.startswith("tellraw @a") and "Player 1 advances to the Castle Age." in c for c in server.log)
    assert any(c.startswith("playsound minecraft:ui.toast.challenge_complete") for c in server.log)
    train.show(g, "Steve", rect)
    assert "Castle Age" not in menus(server)[-1].split("Town Center", 1)[1]
    assert not train.repeatable(g, "CASTLE_AGE")
