"""game/train.py and game/gather.py: the lumber camp researches Two-Man Saw in the Imperial Age, after Bow Saw: the
villagers chop wood faster (#1577)."""
import pytest
from test_castle_gathering import menus, setup

from game import gather, train

SLOT, ITEM, NAME = train.ITEMS["TWO_MAN_SAW"]                          # the menu item of game/data/train.jsonl


def test_the_menu_shows_two_man_saw_in_the_imperial_age_after_bow_saw():
    server, g = setup("LUMBER_CAMP", "BOW_SAW")                    # the Castle Age: not yet
    train.open_menu(g, "Steve", (3, 3))
    assert NAME not in menus(server)[-1] and train.queue(g, "Steve", (3, 3), "TWO_MAN_SAW") is None
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE")                # no Bow Saw: not yet
    train.open_menu(g, "Steve", (3, 3))
    assert NAME not in menus(server)[-1]
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE", "DOUBLE_BIT_AXE", "BOW_SAW")
    train.open_menu(g, "Steve", (3, 3))
    assert f" {SLOT}:{ITEM}:{NAME}:" in menus(server)[-1] and " research" in menus(server)[-1]


def test_after_the_research_the_villagers_chop_wood_10_percent_faster():
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE", "DOUBLE_BIT_AXE", "BOW_SAW")
    old = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    stock, price = dict(g.stock), train.price(g, "TWO_MAN_SAW")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, SLOT) == 1
    assert all(g.stock[r] == stock[r] - v for r, v in price.items())
    train.tick(g, train.seconds(g, "TWO_MAN_SAW"))
    assert "TWO_MAN_SAW" in g.techs
    assert g.work_time("wood") == pytest.approx(old["wood"] / gather.WORK_TECHS["TWO_MAN_SAW"]["wood"])
    assert {r: g.work_time(r) for r in old if r != "wood"} == {r: t for r, t in old.items() if r != "wood"}
    train.open_menu(g, "Steve", (3, 3))
    assert NAME not in menus(server)[-1]


def test_a_civilization_without_two_man_saw_does_not_see_it():
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE", "DOUBLE_BIT_AXE", "BOW_SAW")
    g.data["players"] = {"1": {"civ": "CELTS"}}
    train.open_menu(g, "Steve", (3, 3))
    assert NAME not in menus(server)[-1]
