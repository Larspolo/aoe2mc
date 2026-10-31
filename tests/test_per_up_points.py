"""The point commands of an AI script (#4956), with the examples of airef. The map of test_bot_gather: 32 × 32 tiles,
the town center of the bot (player 2) at tile (21, 21), the town center of player 1 (the foe) at tile (3, 3)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses

HEAD = "(defconst gl-point-x 100)(defconst gl-point-y 101)(defconst gl-other-x 200)(defconst gl-other-y 201)\n"


def run(body, facts="(true)"):
    server, me, b = bot_map()
    me.bots = [b]
    s = per.Script(per.parse(f"{HEAD}(defrule {facts} => {body})"), b)
    s.step()
    return s


def at(s, goal=100):
    return s.goals[goal], s.goals[goal + 1]


def test_get_copy_and_add_points():
    assert at(run("(up-get-point position-center gl-point-x)")) == (16, 16)
    s = run("(up-get-point position-center gl-point-x)(up-copy-point gl-other-x gl-point-x)")
    assert at(s, 200) == (16, 16)
    s = run("(up-get-point position-center gl-other-x)(up-set-target-point gl-other-x)"
            "(up-get-point position-focus gl-point-x)(up-get-point position-target gl-other-x)"
            "(up-add-point gl-point-x gl-other-x c: 1)")
    assert at(s) == (19, 19) and at(s, 200) == (16, 16)


def test_bound_points():
    s = run("(set-goal gl-other-x -5)(set-goal gl-other-y 40)(up-bound-point gl-point-x gl-other-x)")
    assert at(s) == (0, 31)
    assert at(run("(set-goal gl-point-x 0)(set-goal gl-point-y 3)(up-bound-precise-point gl-point-x 0 c: 10)")) == (10, 10)
    s = run("(set-goal gl-point-x 0)(set-goal gl-point-y 3150)(up-bound-precise-point gl-point-x 1 c: 500)")
    assert at(s) == (500, 2699)                                     # 3200 - 1 - 500


def test_cross_and_lerp():
    get = "(up-get-point position-self gl-point-x)(up-get-point position-center gl-other-x)"
    assert at(run(get)) == (21, 21)
    assert at(run(get + "(up-cross-tiles gl-point-x gl-other-x c: 10)")) == (28, 14)
    assert at(run(get + "(up-lerp-percent gl-point-x gl-other-x c: 25)")) == (20, 20)
    assert at(run(get + "(up-lerp-tiles gl-point-x gl-other-x c: 10)")) == (14, 14)


def test_point_distances():
    get = "(up-get-point position-self gl-point-x)(up-get-point position-center gl-other-x)"
    assert run(get + "(up-get-point-distance gl-point-x gl-other-x 300)").goals[300] == 7
    s = run(get)
    assert s.check(("up-point-distance", 100, 200, ">", 5)) and not s.check(("up-point-distance", 100, 200, ">", 7))


def test_target_points():
    s = run("(set-goal gl-point-x 50)(set-goal gl-point-y 7)(up-set-target-point gl-point-x)"
            "(up-get-point position-point gl-other-x)")
    assert s.point == (31, 7) and at(s, 200) == (31, 7)
    s = run("(up-get-point position-center gl-point-x)(up-modify-goal gl-point-x c:* 100)"
            "(up-modify-goal gl-point-y c:* 100)(up-set-precise-target-point gl-point-x)")
    assert s.point == (1600, 1600)


def test_each_position_is_inside_the_map(capsys):
    kinds = ("center", "opposite", "corner", "enemy", "border", "mirror", "flank", "zero", "map-size", "self",
             "focus", "target", "point")
    s = run("(up-get-point position-center gl-point-x)(up-set-target-point gl-point-x)"
            + "".join(f"(up-get-point position-{k} {300 + 2 * i})" for i, k in enumerate(kinds)))
    for i, k in enumerate(kinds):
        assert all(0 <= v < 32 for v in at(s, 300 + 2 * i)), k
    s = run("(set-goal gl-point-x 5)(up-get-point position-object gl-point-x)")       # no target object: (-1, -1) (#5231)
    assert s.goals == {100: -1, 101: -1} and not capsys.readouterr().err
