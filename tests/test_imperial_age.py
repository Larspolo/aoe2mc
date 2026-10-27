"""game/train.py: the town center menu has "Imperial Age" (1000 food and 800 gold, 190 AoE2 seconds). Before the Castle
Age the item is gray; then it needs a castle or 2 types of Castle Age buildings; after the research the sidebar title
shows the Imperial Age, all players see it, and the item leaves the menu (#1081)."""
from test_feudal_age import add
from test_loom import menus, setup
from test_train_menu import IMPERIAL, RALLY

from game import train

NEED = " 5:bell:Imperial Age:1000 food · 800 gold · 190 s · needs a castle or 2 of monastery, university, siege workshop"


def castle_age(**stock):
    server, g = setup(**stock)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    return server, g


def test_in_the_feudal_age_the_item_is_gray_and_a_click_does_nothing():
    server, g = setup(food=1000, gold=1000)
    g.techs.add("FEUDAL_AGE")
    add(g, "CASTLE")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert IMPERIAL in menus(server)[-1]   # Town Watch (slot 6) comes after it (#1454)
    assert menus(server)[-1].endswith(RALLY)
    assert train.order(g, "Steve", rect, 5) == 0 and (g.stock["food"], g.stock["gold"]) == (1000, 1000)
    assert not g.queues.get(rect) and any("Imperial Age: Needs the Castle Age." in c for c in server.log)


def test_in_the_castle_age_the_item_says_what_is_missing_and_a_click_does_nothing():
    server, g = castle_age(food=1000, gold=1000)
    add(g, "MONASTERY", "STABLE")                                       # a Feudal Age building does not count
    rect = train.open_menu(g, "Steve", (3, 3))
    assert NEED + " (1/2)" in menus(server)[-1]   # Town Watch (slot 6) comes after it (#1454)
    assert menus(server)[-1].endswith(RALLY)
    assert train.order(g, "Steve", rect, 5) == 0 and g.stock["food"] == 1000 and not g.queues.get(rect)
    assert any("Imperial Age needs a castle or 2 of" in c for c in server.log)


def test_two_castle_age_buildings_complete_the_need():
    server, g = castle_age(food=1000, gold=1000)
    add(g, "UNIVERSITY")
    g.sites.append({"name": "SIEGE_WORKSHOP", "player": 1, "footprint": [11, 10, 13, 12], "done": True})
    train.open_menu(g, "Steve", (3, 3))
    assert NEED.split(" · needs")[0] + " · research" in menus(server)[-1]   # Town Watch (slot 6) comes after it (#1454)
    assert menus(server)[-1].endswith(RALLY)


def test_a_castle_alone_completes_the_need_and_a_click_queues_the_age_once():
    server, g = castle_age(food=1000, gold=1000)
    add(g, "CASTLE")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert NEED.split(" · needs")[0] + " · research" in menus(server)[-1]   # Town Watch (slot 6) comes after it (#1454)
    assert menus(server)[-1].endswith(RALLY)
    assert train.order(g, "Steve", rect, 5, shift=True) == 1 and (g.stock["food"], g.stock["gold"]) == (0, 200)
    assert train.order(g, "Steve", rect, 5) == 0 and not g.queues[rect][1:]
    assert NEED.split(" · needs")[0] + " · researching" in menus(server)[-1]   # Town Watch (slot 6) comes after it (#1454)
    assert menus(server)[-1].endswith(RALLY)


def test_after_190_seconds_the_player_is_in_the_imperial_age():
    server, g = castle_age(food=1000, gold=800)
    add(g, "CASTLE")
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, 5)
    train.tick(g, 189)
    assert train.age(g) == "Castle Age"
    train.tick(g, 1)
    assert train.age(g) == "Imperial Age" and "IMPERIAL_AGE" in g.techs and not g.queues.get(rect)
    assert server.log.count('scoreboard objectives modify aoe_res displayname "Resources (Imperial Age)"') == 1
    assert 'title @a[team=p1] title {"text": "Imperial Age", "color": "gold"}' in server.log
    assert any(c.startswith("tellraw @a") and "Player 1 advances to the Imperial Age." in c for c in server.log)
    assert any(c.startswith("playsound minecraft:ui.toast.challenge_complete") for c in server.log)
    train.show(g, "Steve", rect)
    assert "Imperial Age" not in menus(server)[-1].split("Town Center", 1)[1]
    assert not train.repeatable(g, "IMPERIAL_AGE")
