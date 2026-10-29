"""#3535: slots 48-50 of each tech tree page show the tree of the previous or next civilization of data/civs.jsonl,
and the civilization of the player does not change."""
from test_techtree import click, setup

from game import civs, diplomacy, techtree, train


def tree(civ):
    server, g = setup(civ)
    diplomacy.open_menu(g, "Steve")
    click(server, g, diplomacy.TECH_TREE_SLOT)
    return server, g


def test_next_civilization_shows_the_name_of_the_next_civilization():
    server, g = tree("CELTS")
    following = techtree.CIVS[techtree.CIVS.index("CELTS") + 1]
    text = click(server, g, techtree.FOLLOWING)
    assert f"49:paper:{techtree.build.pretty(following)}:" in text
    previous = click(server, g, techtree.PREVIOUS)
    assert "49:paper:Celts" in previous


def test_the_castle_page_of_another_civilization_shows_its_unique_unit():
    server, g = tree("CELTS")
    steps = techtree.CIVS.index("BRITONS") - techtree.CIVS.index("CELTS")
    for _ in range(abs(steps)):
        click(server, g, techtree.FOLLOWING if steps > 0 else techtree.PREVIOUS)
    text = click(server, g, techtree.BUILDINGS.index("CASTLE"))
    assert train.ITEMS[civs.UNIQUE["BRITONS"]][2] in text
    assert train.ITEMS[civs.UNIQUE["CELTS"]][2] not in text


def test_the_civilization_of_the_player_does_not_change():
    server, g = tree("CELTS")
    for slot in (techtree.FOLLOWING, techtree.FOLLOWING, techtree.BUILDINGS.index("CASTLE"), techtree.FOLLOWING,
                 techtree.PREVIOUS):
        click(server, g, slot)
    assert civs.real(g) == "CELTS" and g.data["players"][str(g.player)] == {"civ": "CELTS"}
