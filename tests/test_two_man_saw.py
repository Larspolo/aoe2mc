"""game/train.py and game/gather.py: the lumber camp researches Two-Man Saw in the Imperial Age, after Bow Saw and in its
slot (300 food, 200 wood, 100 s): the villagers chop wood 10 % faster (#1577, AoE2 DE wiki infobox and chart)."""
import pytest
from test_castle_gathering import menus, setup

from game import civs, gather, train


def test_the_values_are_those_of_aoe2():
    assert train.AFTER["TWO_MAN_SAW"] == "BOW_SAW"
    assert train.ITEMS["TWO_MAN_SAW"][0] == train.ITEMS["BOW_SAW"][0] and "TWO_MAN_SAW" in train.TRAINS["LUMBER_CAMP"]
    assert gather.WORK_TECHS["TWO_MAN_SAW"] == {"wood": 1.1} and len(train.HELP["TWO_MAN_SAW"]) <= 50
    assert {"CELTS", "FRANKS", "MONGOLS", "ARMENIANS"} <= set(civs.MISSING["TWO_MAN_SAW"])
    assert not {"BRITONS", "VIKINGS", "BURMESE", "JAPANESE"} & set(civs.MISSING["TWO_MAN_SAW"])


def test_the_menu_shows_two_man_saw_in_the_imperial_age_after_bow_saw():
    server, g = setup("LUMBER_CAMP", "BOW_SAW")                    # the Castle Age: not yet
    train.open_menu(g, "Steve", (3, 3))
    assert "Two-Man Saw" not in menus(server)[-1] and train.queue(g, "Steve", (3, 3), "TWO_MAN_SAW") is None
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE")                # no Bow Saw: not yet
    train.open_menu(g, "Steve", (3, 3))
    assert "Two-Man Saw" not in menus(server)[-1]
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE", "DOUBLE_BIT_AXE", "BOW_SAW")
    train.open_menu(g, "Steve", (3, 3))
    assert " 0:book:Two-Man Saw:300 food · 200 wood · 100 s · research " in menus(server)[-1] + " "


def test_after_the_research_the_villagers_chop_wood_10_percent_faster():
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE", "DOUBLE_BIT_AXE", "BOW_SAW")
    old = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 0) == 1
    assert (g.stock["food"], g.stock["wood"]) == (200, 300)
    train.tick(g, 100)
    assert "TWO_MAN_SAW" in g.techs
    assert g.work_time("wood") == pytest.approx(old["wood"] / 1.1)
    assert {r: g.work_time(r) for r in old if r != "wood"} == {r: t for r, t in old.items() if r != "wood"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Two-Man Saw" not in menus(server)[-1]


def test_a_civilization_without_two_man_saw_does_not_see_it():
    server, g = setup("LUMBER_CAMP", "IMPERIAL_AGE", "DOUBLE_BIT_AXE", "BOW_SAW")
    g.data["players"] = {"1": {"civ": "CELTS"}}
    train.open_menu(g, "Steve", (3, 3))
    assert "Two-Man Saw" not in menus(server)[-1]
