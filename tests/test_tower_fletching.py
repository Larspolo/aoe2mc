"""game/train.py: Fletching and Bodkin Arrow give the own towers and the castle +1 attack and +1 range, the town
center +1 attack only (AoE2 DE wiki: "ranged Fortifications +1 attack, +1 range; Town Centers +1 attack"), #1408.
The complete buildings get the values at once (build.retower), a new one when it is complete (build.target)."""
import math

from test_gather import grid
from test_repair import HpServer

from game import build, combat, gather, train

TC, CASTLE, TOWER, HOUSE, NEW = (2, 5, 2, 5), (8, 12, 8, 12), (16, 17, 16, 17), (18, 20, 18, 20), (18, 19, 4, 5)


def setup():
    """A flat 24 × 24 map with an own town center, castle, watch tower and house of the map, in the Castle Age."""
    objects = [{"kind": "building", "name": n, "player": 1, "tile": [(x0 + x1) / 2, (z0 + z1) / 2],
                "footprint": [x0, z0, x1, z1]}
               for n, (x0, x1, z0, z1) in (("TOWN_CENTER", TC), ("CASTLE", CASTLE), ("WATCH_TOWER", TOWER), ("HOUSE", HOUSE))]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}, 1
    server = HpServer({}, {})
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS[:2])
    for rect, name in ((TC, "TOWN_CENTER"), (CASTLE, "CASTLE"), (TOWER, "WATCH_TOWER"), (HOUSE, "HOUSE")):
        server.hp[uuid(rect)] = combat.stats(name).hp - 100            # 100 hit points lost
    return server, g


def uuid(rect):
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def values(server, rect):
    """The hit points, attack and range (blocks, tile size 1) of the last "aoe building" command of the target."""
    c = [c.split() for c in server.log if c.startswith(f"aoe building {uuid(rect)} ")][-1]
    return int(c[3]), int(c[-3]), int(c[-2])


def test_the_buildings_that_shoot_get_the_values_of_fletching_and_bodkin_arrow():
    assert train.TECHS["FLETCHING"]("TOWN_CENTER", combat.stats("TOWN_CENTER")).range == combat.stats("TOWN_CENTER").range
    server, g = setup()
    train.research(g, {"name": "FLETCHING", "player": "Steve"})
    assert values(server, TC) == (2400, 6, 6)                        # +1 attack, the same range
    assert values(server, CASTLE) == (4800, 12, 9)
    assert values(server, TOWER) == (1020, 6, 9)
    assert not any(uuid(HOUSE) in c for c in server.log)             # no attack: no change
    assert server.hp[uuid(TOWER)] == 920                             # the lost hit points stay lost
    train.research(g, {"name": "BODKIN_ARROW", "player": "Steve"})
    assert values(server, TC) == (2400, 7, 6)
    assert values(server, CASTLE) == (4800, 13, 10)
    assert values(server, TOWER) == (1020, 7, 10)


def test_guard_tower_keeps_fletching():
    server, g = setup()
    train.research(g, {"name": "FLETCHING", "player": "Steve"})
    train.research(g, {"name": "GUARD_TOWER", "player": "Steve"})
    assert values(server, TOWER) == (1500, 8, 9)                     # the guard tower 7 attack, 8 range, +1 each


def test_a_tower_that_is_complete_after_the_research_has_the_values():
    server, g = setup()
    train.research(g, {"name": "FLETCHING", "player": "Steve"})
    site = build.found(g, "WATCH_TOWER", NEW)
    build.rise(g, site, math.inf)
    assert values(server, NEW) == (1020, 6, 9)
