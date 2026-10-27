"""Hoardings (#1456): the castle researches it in the Imperial Age (400 food, 400 wood, 75 s; AoE2 wiki "Hoardings"),
and then the complete and the new own castles have 21 % more hit points; a damaged castle keeps its lost hit points."""
import math

from test_gather import grid
from test_loom import menus
from test_repair import HpServer

from game import build, civs, combat, gather, repair, train

CASTLE, NEW = (10, 14, 2, 6), (16, 20, 10, 14)                     # block footprints (x0, x1, z0, z1), tile size 1


def setup(age=3):
    """A flat 24 × 24 map with an own town center and castle, the first `age` ages and the stock for the research."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [12.0, 4.0], "footprint": [10, 2, 14, 6]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}, 1
    server = HpServer({}, {})
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS[:age])
    g.stock.update(food=400, wood=400)
    return server, g


def uuid(rect):
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["HOARDINGS"] == {"food": 400, "wood": 400} and train.TRAIN_TIMES["HOARDINGS"] == 75
    assert train.TECH_AGE["HOARDINGS"] == 3 and len(train.HELP["HOARDINGS"]) <= 50
    assert {"AZTECS", "GOTHS", "WU"} <= set(civs.MISSING["HOARDINGS"]) and "BRITONS" not in civs.MISSING["HOARDINGS"]
    _, g = setup()
    g.techs.add("HOARDINGS")
    assert build.values(g, "CASTLE").hp == 5808 and build.values(g, "TOWN_CENTER") == combat.stats("TOWN_CENTER")


def test_the_castle_menu_shows_it_in_the_imperial_age():
    for age, shown in ((2, False), (3, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (12, 4))
        assert (":book:Hoardings:" in menus(server)[-1]) == shown
    assert " 3:book:Hoardings:400 food · 400 wood · 75 s" in menus(server)[-1]


def test_the_research_gives_the_own_castles_21_percent_more_hit_points():
    server, g = setup()
    server.hp[uuid(CASTLE)] = 4300                                   # the castle lost 500 hit points
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (12, 4)), train.ITEMS["HOARDINGS"][0]) == 1
    train.tick(g, 74)
    assert "HOARDINGS" not in g.techs
    train.tick(g, 1)
    assert "HOARDINGS" in g.techs and server.hp[uuid(CASTLE)] == 5808 - 500
    assert any(c.startswith(f"aoe building {uuid(CASTLE)} 5808 ") for c in server.log)
    assert repair.full(g, "CASTLE", 1) == 5808


def test_a_new_castle_after_the_research_has_the_hit_points_of_hoardings():
    server, g = setup()
    g.techs.add("HOARDINGS")
    site = build.found(g, "CASTLE", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    assert any(c.startswith(f"aoe building {uuid(NEW)} 5808 ") for c in server.log)
