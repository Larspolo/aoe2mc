"""The map facts of an AI script at a point (#4962): terrain, elevation, zone and explored state. The map of
test_bot_gather (32 × 32 tiles, tile size 1) gets a water strip at x >= 29, a land island at (31, 0) and a hill."""
import json
import os

from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses

HEAD = "(defconst gl-x 100)(defconst gl-y 101)\n"
LAND, WATER, HILL = (10, 20), (30, 5), (12, 8)


def script(body="(do-nothing)", old=False):
    server, me, b = bot_map()
    me.bots = [b]
    g = b.g
    for z in range(32):
        for x in range(29, 32):
            if (x, z) != (31, 0):
                g.map.ground[z][x] = None
    if not old:
        g.data["terrain"] = [" ".join("1" if x >= 29 and (x, y) != (31, 0) else "0" for x in range(32)) for y in range(32)]
        g.data["elevation"] = [" ".join("2" if (x, y) == HILL else "0" for x in range(32)) for y in range(32)]
    return per.Script(per.parse(f"{HEAD}(defrule (true) => {body})"), b)


def get(cmd, p, old=False):
    s = script(f"(set-goal gl-x {p[0]})(set-goal gl-y {p[1]})({cmd} gl-x 300)", old)
    s.step()
    return s.goals.get(300)


def fact(cmd, p, op, v):
    s = script(f"(set-goal gl-x {p[0]})(set-goal gl-y {p[1]})")
    s.step()
    return s.check((cmd, 100, op, v))


def test_terrain_and_elevation():
    assert [get("up-get-point-terrain", p) for p in (LAND, WATER, HILL)] == [0, 1, 0]
    assert [get("up-get-point-elevation", p) for p in (LAND, WATER, HILL)] == [0, 0, 2]
    assert fact("up-point-terrain", WATER, "==", 1) and not fact("up-point-terrain", LAND, "==", 1)
    assert fact("up-point-elevation", HILL, ">", 1) and not fact("up-point-elevation", LAND, ">", 1)


def test_an_old_world_has_the_terrain_of_the_water():
    assert [get("up-get-point-terrain", p, old=True) for p in (LAND, WATER, HILL)] == [0, 1, 0]
    assert get("up-get-point-elevation", HILL, old=True) == 0


def test_zones():
    assert [get("up-get-point-zone", p) for p in (LAND, HILL, (0, 0), WATER, (31, 0))] == [1, 1, 1, 2, 3]   # row 0: land, water (29, 0), island
    assert fact("up-point-zone", WATER, "==", 2) and fact("up-point-zone", LAND, "==", 1)


def test_explored():
    s = script("(set-goal gl-x 21)(set-goal gl-y 21)")              # the own town center
    s.step()
    assert s.check(("up-point-explored", 100, "==", "explored-active"))
    s.goals[100], s.goals[101] = WATER
    assert s.check(("up-point-explored", 100, "==", "explored-no"))
    vars(s.bot.g)["fog"]["explored"].add(WATER)
    assert s.check(("up-point-explored", 100, "==", "explored-yes"))
    assert s.check(("up-point-explored", 100, "!=", "explored-no"))


def test_the_world_has_the_tile_grids(tiny_world):
    with open(os.path.join(tiny_world[0], "aoe2mc.json")) as f:
        d = json.load(f)
    n = d["map_size"]
    for key in ("terrain", "elevation"):
        assert len(d[key]) == n and all(len(row.split()) == n for row in d[key])
