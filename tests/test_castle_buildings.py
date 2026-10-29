"""game/build.py: the player builds the Castle Age buildings that the Imperial Age needs (#1162, found by the check #1109)."""
import pytest
from test_build_menu import villager_map

from game import build, train

NEW = ("CASTLE", "MONASTERY", "SIEGE_WORKSHOP", "UNIVERSITY")


@pytest.mark.parametrize("name", NEW)
def test_the_castle_age_building_is_gray_until_the_castle_age(name):
    server, g = villager_map()
    g.techs.add("FEUDAL_AGE")
    icon, _, lore = build.items(g)[build.MENU.index(name)][1:]
    assert icon == "gray_dye" and lore.endswith("Needs the Castle Age")
    g.techs.add("CASTLE_AGE")
    assert build.items(g)[build.MENU.index(name)][1:] == build.items()[build.MENU.index(name)][1:]   # not gray


@pytest.mark.parametrize("built", [("CASTLE",), ("MONASTERY", "UNIVERSITY"), ("SIEGE_WORKSHOP", "UNIVERSITY")])
def test_complete_castle_age_buildings_open_the_imperial_age(built):
    server, g = villager_map()
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    assert train.missing(g, "IMPERIAL_AGE")
    g.sites += [{"name": n, "player": g.player, "done": False} for n in built]
    assert train.missing(g, "IMPERIAL_AGE")                            # a site does not count
    for s in g.sites:
        s["done"] = True
    assert train.missing(g, "IMPERIAL_AGE") is None
