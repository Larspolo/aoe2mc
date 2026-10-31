"""The objects at a point and the walk path to it of an AI script (#4963): up-get-point-contains, up-point-contains,
up-get-path-distance and up-path-distance, with an own small script. The map of test_bot_gather (tile size 1): the
bot (player 2) has a town center on the tiles 20..22 and five villagers b0..b4 at x 24, player 1 the villager p1."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses

SCRIPT = """
(defconst gl-x 100)
(defconst gl-id 102)
(defconst gl-distance 103)
(defrule (true) => (up-get-point-contains gl-x gl-id c: villager-class) (up-get-path-distance gl-x 1 gl-distance))
(defrule (up-point-contains gl-x c: -1) (up-path-distance gl-x 1 < 65535) => (set-goal 104 1))
"""


def script():
    server, me, b = bot_map()
    me.bots = [b]                                                      # run.py: player 1 holds the bots
    b.g.soldiers["m1"] = "MILITIA"
    server.entities["m1"] = {"Pos": (10.5, 64.0, 12.5)}
    s = per.Script(per.parse(SCRIPT), b)
    s.objects(b.g)                                                     # the ids of the own objects
    return s, b


def at(s, x, y):
    """Run the script once at the point (x, y) of goals 100 and 101: (gl-id, gl-distance, goal 104)."""
    s.goals.update({100: x, 101: y, 102: 0, 103: 0, 104: 0})
    s.step()
    return s.goals[102], s.goals[103], s.goals[104]


def test_a_unit_on_the_tile_and_an_empty_tile():
    s, b = script()
    s.target = s.ids["b0"]
    assert at(s, 24, 21) == (s.ids["b2"], 2, 1)                        # villager b2, two tiles from b0
    assert at(s, 10, 12)[0] == -1                                      # the militia: no villager
    assert s.check(("up-point-contains", 100, "c:", "militiaman"))
    assert s.check(("up-point-contains", 100, "c:", -1))
    assert at(s, 12, 12) == (-1, 15, 0)                                # an empty tile: nothing at it; 7 diagonal + 5 steps
    assert s.check(("up-get-point-contains", 100, 105, "c:", -1)) is False and s.goals[105] == -1
    s.goals.update({100: 21, 101: 21})                                 # in the town center
    assert s.check(("up-point-contains", 100, "c:", "town-center")) and not s.warned


def test_a_path_around_a_building_and_a_point_with_no_path():
    s, b = script()
    s.target = s.ids["b2"]                                             # at (24, 21), east of the town center
    assert at(s, 18, 21)[1] == 9 > 6                                   # around the town center, not 6 tiles across
    s.goals.update({100: 18, 101: 21})
    run = [("up-get-path-distance", 100, 1, 106), ("up-get-path-distance", 100, 0, 107)]
    assert all(s.check(c) for c in run) and s.goals[106] == 9 > s.goals[107]   # option 0: a tile near it is enough
    assert at(s, 21, 21)[1:] == (per.NO_PATH, 0)                       # option 1: no free cell in the town center
    s.goals.update({100: 21, 101: 21})
    assert s.check(("up-path-distance", 100, 0, "<", 3))               # option 0: a tile next to it
    assert at(s, 50, 50)[1] == per.NO_PATH                             # off the map
    s.target = None
    assert at(s, 24, 21)[1] == -2                                      # no target object
    assert not s.check(("up-path-distance", 100, 1, "<", 65535)) and not s.warned
