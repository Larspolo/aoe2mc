"""game/build.py and game/train.py: the Feudal Age buildings and units are locked until the Feudal Age (#674)."""
from test_build_menu import villager_map
from menu_line import item
from test_train_archery import menus
from test_train_archery import setup as archery
from test_train_menu import entry

from game import build, train

RANGE = build.MENU.index("ARCHERY_RANGE")


def test_without_a_game_the_build_menu_is_normal():
    icon, label, text = build.items()[RANGE][1:]
    assert icon != "gray_dye" and label == "Archery Range" and "Needs" not in text


def test_in_the_dark_age_the_archery_range_is_gray_and_a_click_chooses_nothing():
    server, g = villager_map()
    assert build.items(g)[RANGE][1:] == ("gray_dye", "Archery Range", build.items()[RANGE][3] + "\nNeeds the Feudal Age")
    assert build.items(g)[0][1] != "gray_dye"                          # a house is a Dark Age building
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
    feudal = [i for i, n in enumerate(build.MENU) if build.AGE.get(n, 0) <= 1]     # the Castle Age ones stay gray (#1162)
    assert [build.items(g)[i] for i in feudal] == [build.items()[i] for i in feudal]
    build.open_menu(g, "Steve")
    g.menus["Steve"]("Steve", RANGE, False)
    assert server.chosen == RANGE + 1 and build.chosen(g, "Steve") == "ARCHERY_RANGE"


def test_in_the_dark_age_a_start_archery_range_shows_a_gray_archer_and_trains_none():
    server, g = archery()
    g.techs.discard("FEUDAL_AGE")
    rect = train.open_menu(g, "Steve", (11, 3))
    cmd = menus(server)[-1]
    assert item(cmd, "Archer").startswith("0:gray_dye:Archer:") and item(cmd, "Archer").endswith(" · Needs the Feudal Age")
    assert item(cmd, "Skirmisher") == entry(g, rect, "SKIRMISHER") + "Needs the Feudal Age"
    for name in ("CAVALRY_ARCHER", "HAND_CANNONEER", "GENITOUR", "ELEPHANT_ARCHER", "MOUNTED_CROSSBOWMAN", "SLINGER",
                 "BOLAS_RIDER"):                                       # gray as before, with the age of the data
        text = item(cmd, train.ITEMS[name][2])
        assert text.startswith(entry(g, rect, name) + "Needs the ") and text.endswith(" Age"), name
    wood = g.stock["wood"]
    assert train.order(g, "Steve", rect, 0) == 0 and g.stock["wood"] == wood and not g.queues.get(rect)
    g.techs.add("FEUDAL_AGE")
    assert train.order(g, "Steve", rect, 0) == 1
