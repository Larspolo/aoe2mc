"""game/train.py: the university researches Guard Tower in the Castle Age (100 food, 250 wood, 30 s; AoE2 DE wiki,
Watch Tower infobox "UpCost") and Keep after it in the Imperial Age (500 food, 350 wood, 75 s; Guard Tower infobox),
#1374. The complete and the new own watch towers get the values of combat.STATS of the new tower; a damaged tower keeps
its lost hit points, as a wall after Fortified Wall (#1326)."""
import math

from test_gather import grid
from test_loom import menus
from test_repair import HpServer

from game import build, combat, gather, train

UNI, MAP, NEW = (8, 12, 8, 12), (16, 17, 16, 17), (18, 19, 4, 5)   # block footprints (x0, x1, z0, z1), tile size 1


def setup(age=2):
    """A flat 24 × 24 map with an own town center, university and watch tower of the map, the first `age` ages, and
    the stock for both researches and a tower."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "UNIVERSITY", "player": 1, "tile": [10, 10], "footprint": [8, 8, 12, 12]},
               {"kind": "building", "name": "WATCH_TOWER", "player": 1, "tile": [16.5, 16.5], "footprint": [16, 16, 17, 17]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}, 1
    server = HpServer({}, {})
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS[:age])
    g.stock.update(food=600, wood=600, stone=200)
    return server, g


def uuid(rect):
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def research(g, name, time):
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (9, 9)), train.ITEMS[name][0]) == 1
    train.tick(g, time - 1)
    assert name not in g.techs
    train.tick(g, 1)
    assert name in g.techs


def test_the_cost_time_age_and_order_are_those_of_aoe2():
    assert train.COSTS["GUARD_TOWER"] == {"food": 100, "wood": 250} and train.TRAIN_TIMES["GUARD_TOWER"] == 30
    assert train.COSTS["KEEP"] == {"food": 500, "wood": 350} and train.TRAIN_TIMES["KEEP"] == 75
    assert (train.TECH_AGE["GUARD_TOWER"], train.TECH_AGE["KEEP"]) == (2, 3) and train.AFTER["KEEP"] == "GUARD_TOWER"
    assert combat.stats("GUARD_TOWER") == combat.Stats(1500, 7, 2, 8, 8, 2.0, {}, ("building", "standard", "stone"))
    assert combat.stats("KEEP") == combat.Stats(2250, 8, 3, 9, 8, 2.0, {}, ("building", "standard", "stone"))


def test_the_university_menu_shows_guard_tower_in_the_castle_age_and_keep_after_it_in_the_imperial_age():
    for age, techs, gt, keep in ((1, (), False, False), (2, (), True, False), (3, (), True, False),
                                 (3, ("GUARD_TOWER",), False, True)):
        server, g = setup(age)
        g.techs |= set(techs)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Guard Tower:" in menus(server)[-1], ":book:Keep:" in menus(server)[-1]) == (gt, keep)
    assert "3:book:Keep:500 food · 350 wood · 75 s · research" in menus(server)[-1]
    server, g = setup(3)
    assert train.queue(g, "Steve", (9, 9), "KEEP") is None          # not before Guard Tower


def test_the_research_gives_the_towers_the_values_of_the_guard_tower_and_then_of_the_keep():
    server, g = setup(3)
    server.hp[uuid(MAP)] = 520                                     # 500 hit points lost
    research(g, "GUARD_TOWER", 30)
    assert server.hp[uuid(MAP)] == 1000                            # +480 hit points
    assert any(c.startswith(f"aoe building {uuid(MAP)} 1500 2 8 ") and c.split()[12:14] == ["7", "8"]   # attack, range
               for c in server.log)
    assert f"aoe label {uuid(MAP)} Guard Tower" in server.log
    assert not any(c.startswith("summon ") for c in server.log)    # the same target
    research(g, "KEEP", 75)
    assert server.hp[uuid(MAP)] == 1750                            # +750 hit points
    assert any(c.startswith(f"aoe building {uuid(MAP)} 2250 3 9 ") for c in server.log)
    assert build.line(g, "WATCH_TOWER") == build.line(g, "GUARD_TOWER") == "KEEP"
    assert build.line(g, "HOUSE") == "HOUSE"


def test_a_destroyed_tower_stays_destroyed():
    server, g = setup()
    research(g, "GUARD_TOWER", 30)                                 # no score: no target
    assert not any(uuid(MAP) in c for c in server.log if "players get" not in c)


def test_a_new_watch_tower_after_the_research_has_the_values_of_the_guard_tower():
    server, g = setup()
    g.techs.add("GUARD_TOWER")
    site = build.found(g, "WATCH_TOWER", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    assert any(c.startswith(f"aoe building {uuid(NEW)} 1500 2 8 ") for c in server.log)
    assert f"aoe label {uuid(NEW)} Guard Tower" in server.log


def test_villagers_repair_an_upgraded_tower_to_the_hit_points_of_its_new_tower():
    from game import repair
    _, g = setup()
    assert repair.full(g, "WATCH_TOWER", 1) == 1020
    g.techs.add("GUARD_TOWER")
    assert repair.full(g, "WATCH_TOWER", 1) == 1500
