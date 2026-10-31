"""The airef terrain names (pTerrain) of an AI script: a terrain name compares as its AoE2 terrain ID (#5128).
The map of test_bot_gather has grass (ID 0) on land and water (ID 1) on the water strip."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses

HEAD = "(defconst gl-x 100)(defconst gl-y 101)\n"
LAND, WATER = (10, 20), (30, 5)


def script(body="(do-nothing)"):
    server, me, b = bot_map()
    me.bots = [b]
    g = b.g
    g.data["terrain"] = [" ".join("1" if x >= 29 and (x, y) != (31, 0) else "0" for x in range(32)) for y in range(32)]
    return per.Script(per.parse(f"{HEAD}(defrule (true) => {body})"), b)


def fact(p, op, name):
    s = script(f"(set-goal gl-x {p[0]})(set-goal gl-y {p[1]})")
    s.step()
    return s.check(("up-point-terrain", 100, op, name))


def test_a_tile_matches_its_terrain_name():
    assert fact(LAND, "==", "terrain-grass") and not fact(LAND, "==", "terrain-water")
    assert fact(WATER, "==", "terrain-water") and fact(WATER, "!=", "terrain-grass")


def test_a_goal_gets_the_terrain_and_matches_its_name():
    s = script(f"(set-goal gl-x {WATER[0]})(set-goal gl-y {WATER[1]})(up-get-point-terrain gl-x 300)")
    s.step()
    assert s.goals[300] == 1
    assert s.check(("goal", 300, "==", "terrain-water")) and not s.check(("goal", 300, "==", "terrain-grass"))


def test_an_unknown_terrain_name_warns_once_and_is_false(capsys):
    s = script(f"(set-goal gl-x {LAND[0]})(set-goal gl-y {LAND[1]})")
    s.step()
    assert not s.check(("up-point-terrain", 100, "==", "terrain-no-such-terrain"))
    assert not s.check(("up-point-terrain", 100, "==", "terrain-no-such-terrain"))
    assert capsys.readouterr().err.count("terrain-no-such-terrain") == 1
