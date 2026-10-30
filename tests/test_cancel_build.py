"""game/gather.py: on Paper a right click with the command stick ends the choice of a building (#2056; the left click
places it, #4703). The score aoe_build goes to 0, the sneak clicks of build.place forget their row, and build.ghosts
clears the ghost."""
from game import build

from test_deselect import paper


def test_a_right_click_ends_the_building_choice():
    server, g = paper()
    g.select("v-1")
    server.scores[build.OBJECTIVE] = 1 + build.MENU.index("HOUSE")
    g.rows, g.wall_start = {"Steve": ("HOUSE", "Steve 1")}, {"Steve": (4, 4)}
    g.click("Steve")
    assert f"scoreboard players set Steve {build.OBJECTIVE} 0" in server.log
    assert g.selected == {"v-1"} and g.rows == {} and g.wall_start == {}
    server.scores.pop(build.OBJECTIVE)                                 # the fake server has no "set"
    g.ghosts = {"Steve": ["HOUSE", "green", None, None]}
    build.ghosts(g)
    assert "aoe ghost-clear Steve" in server.log and g.ghosts == {}


def test_a_right_click_without_a_choice_sets_no_score():
    server, g = paper()
    g.select("v-1")
    g.click("Steve")
    assert not any(c.startswith("scoreboard players set") and build.OBJECTIVE in c for c in server.log)
