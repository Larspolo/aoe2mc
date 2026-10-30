"""game/gather.py: on Paper a left click with the command stick also ends the choice of a building (#2056). The
score aoe_build goes to 0, the sneak clicks of build.place forget their row, and build.ghosts clears the ghost."""
from test_deselect import paper

from game import build, gather


def left(server, g):
    server.scores[gather.LEFT] = 1
    g.deselect()                                                       # as clicks() does after build.tick
    if f"scoreboard players set Steve {build.OBJECTIVE} 0" in server.log:
        server.scores.pop(build.OBJECTIVE, None)                       # the fake server has no "set"


def test_a_left_click_ends_the_building_choice():
    server, g = paper()
    g.select("v-1")
    server.scores[build.OBJECTIVE] = 1 + build.MENU.index("HOUSE")
    g.rows, g.wall_start = {"Steve": ("HOUSE", "Steve 1")}, {"Steve": (4, 4)}
    left(server, g)
    assert g.selected == set() and build.OBJECTIVE not in server.scores
    assert g.rows == {} and g.wall_start == {}
    g.ghosts = {"Steve": ["HOUSE", "green", None, None]}
    build.ghosts(g)
    assert "aoe ghost-clear Steve" in server.log and g.ghosts == {}


def test_a_left_click_without_a_choice_only_deselects():
    server, g = paper()
    g.select("v-1")
    left(server, g)
    assert g.selected == set()
    assert not any(c.startswith("scoreboard players set") and build.OBJECTIVE in c for c in server.log)
