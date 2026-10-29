"""#3534: the page "Buildings" of the tech tree shows the buildings of the civilization by age, and a building that the
civilization does not have is gray."""
from test_techtree import click, setup

from game import build, civs, diplomacy, techtree


def buildings_page(civ=None):
    server, g = setup(civ)
    diplomacy.open_menu(g, "Steve")
    click(server, g, diplomacy.TECH_TREE_SLOT)
    return click(server, g, techtree.ALL)


def row_of(name):
    """The row (age) of a building on the first page, for all civilizations."""
    slots = techtree.pages([n for n in build.ICONS])[0]
    return next(s // 9 for s, n in slots.items() if n == name)


def test_the_barracks_is_in_row_0_and_the_castle_in_row_2():
    assert row_of("BARRACKS") == 0
    assert row_of("CASTLE") == 2


def test_a_building_that_the_civilization_does_not_have_is_gray():
    assert "gray_stained_glass_pane:Lumber Camp:Not in the tech tree of Incas" in buildings_page("INCAS")


def test_the_krepost_shows_only_for_its_civilization():
    assert "Krepost" in buildings_page("BULGARIANS")
    assert "Krepost" not in buildings_page("CELTS")
    assert "KREPOST" in civs.ONLY and civs.ONLY["KREPOST"] == {"BULGARIANS"}


def test_the_back_item_returns_to_the_page_of_buildings():
    assert "45:arrow:Back" in buildings_page("CELTS")
