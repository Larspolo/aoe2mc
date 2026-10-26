"""game/build.py and game/train.py: the Feudal Age buildings and units are locked until the Feudal Age (#674)."""
from test_build_menu import villager_map
from test_train_archery import menus
from test_train_archery import setup as archery
from test_train_menu import RALLY, SKIRM

from game import build, train

RANGE = build.MENU.index("ARCHERY_RANGE")


def test_without_a_game_the_build_menu_is_normal():
    assert build.items()[RANGE][1:] == ("target", "Archery Range", "175 wood\n50 s")


def test_in_the_dark_age_the_archery_range_is_gray_and_a_click_chooses_nothing():
    server, g = villager_map()
    assert build.items(g)[RANGE][1:] == ("gray_dye", "Archery Range", "175 wood\n50 s\nNeeds the Feudal Age")
    assert build.items(g)[0][1] == "spruce_stairs"                     # a house is a Dark Age building
    build.open_menu(g, "Steve")
    g.menus["Steve"]("Steve", RANGE, False)
    assert build.chosen(g, "Steve") is None and "Steve" in g.menus    # no choice, the menu stays open


def test_in_the_dark_age_a_trigger_choice_of_the_archery_range_places_no_site():
    server, g = villager_map()
    g.stock["wood"] = 500
    assert build.place(g, "Steve", "ARCHERY_RANGE", (8.5, 65.6, 12.5), (0.0, -0.5, -0.87)) is None
    assert not g.sites and g.stock["wood"] == 500
    assert any("Archery Range: Needs the Feudal Age." in c for c in server.log)


def test_after_the_feudal_age_the_items_are_normal():
    server, g = villager_map()
    g.techs.add("FEUDAL_AGE")
    assert build.items(g) == build.items()
    build.open_menu(g, "Steve")
    g.menus["Steve"]("Steve", RANGE, False)
    assert server.chosen == RANGE + 1 and build.chosen(g, "Steve") == "ARCHERY_RANGE"


def test_in_the_dark_age_a_start_archery_range_shows_a_gray_archer_and_trains_none():
    server, g = archery()
    g.techs.discard("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    assert menus(server)[-1] == "aoe menu Steve Archery Range 0:gray_dye:Archer:25 wood · 45 gold · 35 s · " \
                                "Needs the Feudal Age" + SKIRM.replace("drowned_spawn_egg", "gray_dye").replace(
                                    "queue 0/15", "Needs the Feudal Age") + RALLY
    assert train.order(g, "Steve", rect, 0) == 0 and g.stock["wood"] == 25 and not g.queues.get(rect)
    g.techs.add("FEUDAL_AGE")
    assert train.order(g, "Steve", rect, 0) == 1
