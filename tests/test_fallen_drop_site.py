"""game/ruins.py: a fallen own drop site (lumber camp, town center, dock) leaves the drop sites of each side, so that
the villagers and fishing ships with a load go to another drop site and each side can build on its ground (#3009)."""
from test_drop_sites import Server, building, data
from test_trade_cog import FAR, HOME, docks_map

from game import build, fleet, gather, ruins

CAMP, TC = (4, 8, 4, 8), (30, 34, 30, 34)                           # block footprints (x0, x1, z0, z1)


def cells(rect):
    return {(x, z) for x in range(rect[0], rect[1]) for z in range(rect[2], rect[3])}


def villager(g):
    v = g.villagers["v"] = gather.Villager("v", (2.5, 64.0, 7.5))
    v.state, v.load, v.tree = "to_drop", 7, None
    g.go(v, "to_drop", g.drop_goals(v))                                # the walk to the nearest wood site
    return v


def test_a_villager_with_wood_takes_it_to_another_drop_site_when_its_camp_falls():
    g = gather.Gather(Server(), data(building("TOWN_CENTER", 30, 30), building("LUMBER_CAMP", 4, 4)), start={})
    v = villager(g)
    assert v.path[-1] in g.map.around(cells(CAMP))
    ruins.fall(g, CAMP)
    assert cells(CAMP) not in g.map.drops["wood"]
    assert v.state == "to_drop" and v.load == 7 and v.path[-1] in g.map.around(cells(TC))


def test_a_villager_with_a_load_stands_idle_when_no_other_drop_site_is_left():
    g = gather.Gather(Server(), data(building("LUMBER_CAMP", 4, 4)), start={})
    v = villager(g)
    ruins.fall(g, CAMP)
    assert v.state == "idle" and v.load == 7 and not g.map.drops["wood"]


def test_the_ground_of_a_fallen_town_center_is_free_for_a_new_building():
    g = gather.Gather(Server(), data(building("TOWN_CENTER", 30, 30)), start={})
    assert not build.free(g, TC)
    ruins.fall(g, TC)
    assert build.free(g, TC) and not g.map.drops["wood"] and not g.map.blocked & cells(TC)


def test_a_fishing_ship_with_a_catch_sails_to_another_dock_when_its_dock_falls():
    server, g = docks_map()
    far, home = FAR, HOME
    ship = g.ships["s"] = gather.Villager("s", (20.5, 64.0, 33.5))
    ship.state, ship.load = "to_drop", 15
    fleet.sail_to(g, ship, "to_drop", g.map.around(cells(far), water=True))
    ruins.fall(g, far)
    assert ship.state == "to_drop" and ship.path[-1] in g.map.around(cells(home), water=True)
    assert far not in g.map.docks and cells(far) not in g.map.docks
