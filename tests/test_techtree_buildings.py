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
    slots = techtree.rows([n for n in build.ICONS])[0]
    return next(s // 9 for s, n in slots.items() if n == name)


def test_a_building_is_in_the_row_of_its_age():
    for name in ("BARRACKS", "CASTLE"):
        assert row_of(name) == techtree.age(name), name


def test_a_building_that_the_civilization_does_not_have_is_gray():
    civ, name = next((c, n) for n in build.ICONS if n not in civs.ONLY for c in sorted(civs.MISSING.get(n, ())))
    text = f"gray_stained_glass_pane:{build.pretty(name)}:Not in the tech tree of {build.pretty(civ)}"
    assert text in buildings_page(civ)


def test_a_building_of_some_civilizations_shows_only_for_them():
    name, owners = next((n, o) for n, o in civs.ONLY.items() if n in build.ICONS)
    other = next(c for c in techtree.CIVS if c not in owners)
    assert build.pretty(name) in buildings_page(min(owners))
    assert build.pretty(name) not in buildings_page(other)


def test_the_back_item_returns_to_the_page_of_buildings():
    assert "45:arrow:Back" in buildings_page("CELTS")
