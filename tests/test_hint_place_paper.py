"""game/hints.py: on Paper a left click places the chosen building and a right click cancels it (#4703), so the
building hint of Paper has its own text (#5483); vanilla keeps the right click text."""
from test_hints import game

from game import hints, lang


def building_hint(paper):
    _, g, _ = game()
    g.paper = paper
    g.ghosts = {"Steve": ["LUMBER_CAMP", "green"]}
    return hints.state(g, "Steve")


def test_paper_shows_the_left_click_hint():
    kind, text = building_hint(True)
    assert kind == "building" and text == lang.text("aoe2mc.hints.building_paper", "Lumber Camp")


def test_vanilla_shows_the_right_click_hint():
    kind, text = building_hint(False)
    assert kind == "building" and text == lang.text("aoe2mc.hints.building", "Lumber Camp")
