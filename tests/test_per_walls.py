"""game/per.py: an AI script walls its town with build-wall, build-gate and wall-completed-percentage (#4740)."""
import math

from test_bot_gather import bot_map

from game import per

WALL = "(defrule (true) => (build-wall 1 palisade-wall))"
TC = (21, 21)                                                          # the middle tile of the town center of player 2


def script(text, **stock):
    server, me, b = bot_map()
    b.g.stock.update(stock)
    return per.Script(per.parse(text), b), b


def walls(b):
    return [s for s in b.g.sites if s["name"] == "PALISADE_WALL"]


def tile(site):
    return site["footprint"][0], site["footprint"][2]                  # tile size 1


def norm(t):
    """The distance of the octagon of per.ring from the town center."""
    dx, dz = abs(t[0] - TC[0]), abs(t[1] - TC[1])
    return math.ceil(max(dx, dz, (dx + dz) / (1 + per.OCTAGON)))


def test_one_build_wall_puts_one_side_of_the_ring():
    s, b = script(WALL + " (defrule (true) => (disable-self))", wood=1000)
    s.step()
    side = next(x for x in s.rings[1] if x)
    sites = walls(b)
    assert sites and {tile(x) for x in sites} in [set(x) for x in s.rings[1]]
    assert {norm(tile(x)) for x in sites} == {per.PERIMETERS[1][0]}   # the town is small: the nearest radius
    assert b.g.stock["wood"] == 1000 - 3 * len(sites) and len(side) > 1
    assert any(v.site in sites for v in b.g.villagers.values())        # a villager builds the line


def test_the_stock_limits_the_tiles():
    s, b = script(WALL, wood=7)
    s.step()
    assert len(walls(b)) == 2 and b.g.stock["wood"] == 1


def test_the_ring_leaves_the_town_and_the_resources_free():
    s, b = script(WALL, wood=5000)
    for _ in range(8):
        s.step()
    ring = {t for side in s.rings[1] for t in side}
    assert {tile(x) for x in walls(b)} == ring                         # all sides
    g = b.g
    own = [o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == 2]
    inner = {(x, z) for x0, z0, x1, z1 in own for x in range(x0, x1) for z in range(z0, z1)} | set(g.map.trees) | \
        set(g.map.bushes) | {t for m in g.map.mines.values() for t in m} | set(g.map.mine_at)
    assert inner and not inner & ring
    assert all(norm(t) < per.PERIMETERS[1][0] - 1 for t in inner if norm(t) <= per.PERIMETERS[1][1])


def test_the_ring_grows_around_a_far_drop_site_and_stops_at_the_map_edge():
    server, me, b = bot_map()
    b.g.data["objects"].append({"kind": "building", "name": "MILL", "player": 2, "footprint": [20, 8, 22, 10]})
    s = per.Script(per.parse(WALL), b)
    sides = s.ring(1)
    ring = [t for side in sides for t in side]
    assert {norm(t) for t in ring} == {norm((21, 8)) + 2}              # one free tile outside the mill
    assert all(0 <= x < 32 and 0 <= z < 32 for x, z in ring)           # the tiles off the map are cut


def test_wall_completed_percentage_rises_as_the_sites_complete():
    s, b = script(WALL + " (defrule (wall-completed-percentage 1 >= 50) => (set-goal 1 1))", wood=5000)
    for _ in range(8):
        s.step()
    assert s.walled(1) == 0 and 1 not in s.goals
    sites = walls(b)
    for x in sites[:len(sites) // 2 + 1]:
        x["progress"] = 1.0
    assert 50 <= s.walled(1) < 100
    s.step()
    assert s.goals[1] == 1
    for x in sites:
        x["progress"] = 1.0
    assert s.walled(1) == 100


def test_the_villagers_of_the_bot_build_the_wall():
    s, b = script(WALL + " (defrule (true) => (disable-self))", wood=1000)
    s.step()
    for _ in range(600):
        b.step()
    assert s.walled(1) > 0


def test_build_gate_puts_a_gate_on_4_tiles_of_the_ring():
    s, b = script(WALL + " (defrule (true) => (set-strategic-number sn-gate-type-for-wall 1))", wood=5000)
    for _ in range(8):
        s.step()
    s.rules = per.parse("(defrule (true) => (build-gate 1) (disable-self))")
    s.step()
    (gate,) = [x for x in b.g.sites if x["name"] == "PALISADE_GATE"]
    x0, x1, z0, z1 = gate["footprint"]
    tiles = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    assert len(tiles) == 4 and any(tiles <= set(side) for side in s.rings[1])
    assert not tiles & {tile(x) for x in walls(b)}                     # the gate replaced 4 wall sites
    assert any(v.site is gate for v in b.g.villagers.values())


def test_no_gate_without_a_wall_and_no_second_gate_on_a_side():
    s, b = script("(defrule (true) => (set-strategic-number sn-gate-type-for-wall 1) (build-gate 1))", wood=5000)
    s.step()
    assert not [x for x in b.g.sites if x["name"] == "PALISADE_GATE"]
    s.rules = per.parse(WALL)
    for _ in range(8):
        s.step()
    s.rules = per.parse("(defrule (true) => (build-gate 1))")
    s.step()
    s.step()
    gates = [x for x in b.g.sites if x["name"] == "PALISADE_GATE"]
    sides = [next(k for k, side in enumerate(s.rings[1]) if s.gate_tiles(x) <= set(side)) for x in gates]
    assert len(gates) == 2 and len(set(sides)) == 2


def test_wall_actions_give_no_warning(capsys):
    s, b = script("(defrule (true) => (enable-wall-placement 1) (build-wall 2 stone-wall) (build-gate 2))"
                  " (defrule (wall-completed-percentage 2 < 100) => (do-nothing))")
    s.step()
    assert capsys.readouterr().err == "" and not b.g.sites            # the stone wall needs the Feudal Age
