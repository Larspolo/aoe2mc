"""game/train.py: the university researches Guard Tower in the Castle Age (AoE2 DE wiki, Watch Tower
infobox "UpCost") and Keep after it in the Imperial Age (Guard Tower infobox), #1374. The complete and the new own watch towers get the values of combat.STATS of the new tower; a damaged tower keeps
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
    g.stock.update(food=10000, wood=10000, stone=10000)
    return server, g


def uuid(rect):
    x0, x1, z0, z1 = rect
    return combat.target_uuid([x0, z0, x1, z1])


def research(g, name):
    time = train.TRAIN_TIMES[name]
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (9, 9)), train.ITEMS[name][0]) == 1
    train.tick(g, time - 1)
    assert name not in g.techs
    train.tick(g, 1)
    assert name in g.techs


def item(name):
    return f":{train.ITEMS[name][1]}:{train.ITEMS[name][2]}:"


def building(s):
    """The start of the "aoe building" command of the map tower with the values s."""
    return f"aoe building {uuid(MAP)} {s.hp} {s.melee} {s.pierce} "


def test_the_university_menu_shows_guard_tower_in_the_castle_age_and_keep_after_it_in_the_imperial_age():
    for age, techs, gt, keep in ((1, (), False, False), (2, (), True, False), (3, (), True, False),
                                 (3, ("GUARD_TOWER",), False, True)):
        server, g = setup(age)
        g.techs |= set(techs)
        train.open_menu(g, "Steve", (9, 9))
        assert (item("GUARD_TOWER") in menus(server)[-1], item("KEEP") in menus(server)[-1]) == (gt, keep)
    server, g = setup(3)
    assert train.queue(g, "Steve", (9, 9), "KEEP") is None          # not before Guard Tower


def test_the_research_gives_the_towers_the_values_of_the_guard_tower_and_then_of_the_keep():
    server, g = setup(3)
    guard, keep = combat.stats("GUARD_TOWER"), combat.stats("KEEP")
    server.hp[uuid(MAP)] = combat.stats("WATCH_TOWER").hp - 500    # 500 hit points lost
    research(g, "GUARD_TOWER")
    assert server.hp[uuid(MAP)] == guard.hp - 500                  # the lost hit points stay lost
    assert any(c.startswith(building(guard)) and c.split()[12:14] == [str(guard.attack), str(guard.range)]
               for c in server.log)
    assert f"aoe label {uuid(MAP)} Guard Tower" in server.log
    assert not any(c.startswith("summon ") for c in server.log)    # the same target
    research(g, "KEEP")
    assert server.hp[uuid(MAP)] == keep.hp - 500
    assert any(c.startswith(building(keep)) for c in server.log)
    assert build.line(g, "WATCH_TOWER") == build.line(g, "GUARD_TOWER") == "KEEP"
    assert build.line(g, "HOUSE") == "HOUSE"


def test_a_destroyed_tower_stays_destroyed():
    server, g = setup()
    research(g, "GUARD_TOWER")                                     # no score: no target
    assert not any(uuid(MAP) in c for c in server.log if "players get" not in c)


def test_a_new_watch_tower_after_the_research_has_the_values_of_the_guard_tower():
    server, g = setup()
    g.techs.add("GUARD_TOWER")
    site = build.found(g, "WATCH_TOWER", NEW)
    server.log.clear()
    build.rise(g, site, math.inf)
    s = combat.stats("GUARD_TOWER")
    assert any(c.startswith(f"aoe building {uuid(NEW)} {s.hp} {s.melee} {s.pierce} ") for c in server.log)
    assert f"aoe label {uuid(NEW)} Guard Tower" in server.log


def test_villagers_repair_an_upgraded_tower_to_the_hit_points_of_its_new_tower():
    from game import repair
    _, g = setup()
    assert repair.full(g, "WATCH_TOWER", 1) == combat.stats("WATCH_TOWER").hp
    g.techs.add("GUARD_TOWER")
    assert repair.full(g, "WATCH_TOWER", 1) == combat.stats("GUARD_TOWER").hp
