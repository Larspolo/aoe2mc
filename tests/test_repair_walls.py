"""game/repair.py: selected villagers repair an own damaged wall tile or gate of the game program (#1360), as a
building in AoE2 DE (AoE2 wiki "Repairing"): the same rate, half the build cost, up to the hit points of its design
and age (combat.wall)."""
from test_gather import grid
from test_repair import HpServer

from game import build, combat, gather, repair

WALL, GATE = (4, 5, 4, 5), (8, 12, 4, 5)                           # block footprints (x0, x1, z0, z1), tile size 1


def setup(wall=100, gate=650, techs=(), wood=10, stone=50):
    """A flat 24 × 24 map with a complete own palisade wall tile and gate (game program sites) at the hit points wall
    and gate, and an own villager "v0" next to them."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [6.5, 6.5]}]
    server = HpServer({"v0": {"Pos": (6.5, 64.0, 6.5)}}, {repair.uuid(WALL): wall, repair.uuid(GATE): gate})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={"wood": wood, "stone": stone}).setup()
    g.techs = set(techs)
    for name, rect in (("PALISADE_WALL", WALL), ("GATE", GATE)):
        g.sites.append({"name": name, "player": 1, "footprint": rect, "progress": 1.0, "done": True})
        g.map.blocked |= {(x, z) for x in range(rect[0], rect[1]) for z in range(rect[2], rect[3])}
    g.choose(set(g.villagers), "v0")
    return server, g


def run(g):
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 3000:
        g.step()
        steps += 1


def test_the_full_hit_points_of_a_wall_are_those_of_its_design_and_age():
    _, g = setup()
    stone = []
    for techs, age in (((), 0), ({"FEUDAL_AGE", "CASTLE_AGE"}, 2), ({"FEUDAL_AGE", "CASTLE_AGE", "FORTIFIED_WALL"}, 2)):
        g.techs = set(techs)
        for name in ("PALISADE_WALL", "STONE_WALL", "GATE"):
            assert repair.full(g, name, 1) == combat.WALLS[build.design(g, name, 1)][0][age], (name, techs)
        stone.append(repair.full(g, "STONE_WALL", 1))
    assert stone[2] != stone[1]                                    # the stone walls of the player are fortified (#1326)
    assert repair.full(g, "HOUSE", 1) == combat.stats("HOUSE").hp
    for name in ("PALISADE_WALL", "GATE"):
        assert repair.cost(g, name) == {r: v / 2 for r, v in build.price(g, name).items()}


def test_a_villager_repairs_a_damaged_palisade_wall_tile():
    server, g = setup()
    assert repair.order(g, "Steve", (4, 4)) == WALL
    run(g)
    full = repair.full(g, "PALISADE_WALL", 1)
    assert server.hp[repair.uuid(WALL)] == full                    # the Dark Age hit points
    assert abs(10 - g.stock["wood"] - repair.cost(g, "PALISADE_WALL")["wood"] * (full - 100) / full) <= 1


def test_a_villager_repairs_a_damaged_gate_at_the_building_rate():
    server, g = setup(gate=650, techs={"FEUDAL_AGE"})
    assert repair.order(g, "Steve", (10, 4)) == GATE
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)                                            # 8 AoE2 s
    assert server.hp[repair.uuid(GATE)] == 650 + round(repair.RATE * 8)
    run(g)
    full = repair.full(g, "GATE", 1)
    assert server.hp[repair.uuid(GATE)] == full                    # the Feudal Age hit points
    assert abs(50 - g.stock["stone"] - repair.cost(g, "GATE")["stone"] * (full - 650) / full) <= 1


def test_a_click_on_an_undamaged_or_destroyed_wall_is_no_repair_order():
    server, g = setup(wall=repair.full(setup()[1], "PALISADE_WALL", 1), gate=0)
    assert repair.order(g, "Steve", (4, 4)) is None and repair.order(g, "Steve", (9, 4)) is None
    assert g.villagers["v0"].state == "idle"
